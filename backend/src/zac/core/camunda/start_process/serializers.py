from dataclasses import dataclass
from typing import Dict, List, Union

from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework.generics import get_object_or_404
from zgw_consumers.api_models.constants import RolTypes
from zgw_consumers.drf.serializers import APIModelSerializer

from zac.api.context import get_zaak_context
from zac.camunda.data import Task
from zac.camunda.user_tasks import Context, register, usertask_context_serializer
from zac.core.api.serializers import (
    EigenschapSerializer,
    InformatieObjectTypeSerializer,
    RolSerializer,
    RolTypeSerializer,
)
from zac.core.services import (
    get_documenten,
    get_rollen,
    get_roltypen,
    get_zaak_eigenschappen,
    resolve_documenten_informatieobjecttypen,
)

from .models import (
    CamundaStartProcess,
    ProcessEigenschap,
    ProcessEigenschapChoice,
    ProcessInformatieObject,
    ProcessRol,
)
from .utils import (
    get_required_process_informatie_objecten,
    get_required_rollen,
    get_required_zaakeigenschappen,
)


class ProcessEigenschapChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessEigenschapChoice
        fields = ("label", "value")


class ProcessEigenschapSerializer(serializers.ModelSerializer):
    choices = ProcessEigenschapChoiceSerializer(
        many=True,
        required=False,
        help_text=_("Possible choices related to the EIGENSCHAP."),
        source="processeigenschapchoice_set",
    )
    eigenschap = EigenschapSerializer(
        required=True, help_text=_("The EIGENSCHAP related to the ZAAKEIGENSCHAP.")
    )

    class Meta:
        model = ProcessEigenschap
        fields = ("choices", "eigenschap", "label", "value", "default")


class ProcessInformatieObjectSerializer(serializers.ModelSerializer):
    informatieobjecttype = InformatieObjectTypeSerializer(
        required=True,
        help_text=_("The INFORMATIEOBJECTTYPE related to the ZAAKINFORMATIEOBJECT."),
    )
    already_uploaded_informatieobjecten = serializers.ListField(
        child=serializers.URLField(),
        required=False,
        help_text=_("URL-references of already uploaded documents."),
    )

    class Meta:
        model = ProcessInformatieObject
        fields = (
            "informatieobjecttype",
            "allow_multiple",
            "label",
            "value",
        )


class ProcessRolSerializer(serializers.ModelSerializer):
    roltype = RolTypeSerializer(
        _("roltype"), required=True, help_text=_("The ROLTYPE related to the ROL.")
    )

    class Meta:
        model = ProcessRol
        fields = ("roltype", "label", "value", "betrokkene_type", "default")


class ZaakProcessEigenschapSerializer(serializers.Serializer):
    naam = serializers.CharField(
        help_text=_(
            "Name of EIGENSCHAP. Must match EIGENSCHAP name as defined in CATALOGI API."
        )
    )
    waarde = serializers.CharField(
        help_text=_(
            "Value of ZAAKEIGENSCHAP. Must be able to be formatted as defined by the EIGENSCHAP spec."
        )
    )


class ConfigureZaakProcessSerializer(serializers.Serializer):
    bijlagen = serializers.HiddenField(default=[])
    rollen = serializers.HiddenField(default=[])
    zaakeigenschappen = serializers.HiddenField(default=[])

    @property
    def zaakcontext(self):
        if not hasattr(self, "_zaakcontext"):
            self._zaakcontext = get_zaak_context(
                self.context["task"], require_zaaktype=True, require_documents=True
            )
        return self._zaakcontext

    @property
    def camunda_start_process(self):
        if not hasattr(self, "_camunda_start_process"):
            try:
                camunda_start_process = CamundaStartProcess.objects.get(
                    zaaktype_catalogus=self.zaakcontext.zaaktype.catalogus,
                    zaaktype_identificatie=self.zaakcontext.zaaktype.identificatie,
                ).prefetch_related(
                    "processeigenschap_set",
                    "processinformatieobject_set",
                    "processrol_set",
                )
            except ObjectDoesNotExist:
                raise serializers.ValidationError(
                    _(
                        "No camunda start process form is found for zaaktype with identificatie {zaaktype_identificatie} within catalogus {zaaktype_catalogus}"
                    ).format(
                        zaaktype_identificatie=self.zaakcontext.zaaktype.identificatie,
                        zaaktype_catalogus=self.zaakcontext.zaaktype.catalogus,
                    )
                )
            self._camunda_start_process = camunda_start_process
        return self._camunda_start_process

    def validate_bijlagen(self, bijlagen):
        # Validate that zaakeigenschappen related to zaak match required zaakeigenschappen.
        documenten, gone = get_documenten(self.zaakcontext.zaak)
        documenten = resolve_documenten_informatieobjecttypen(documenten)
        iots = [doc.informatieobjecttype.omschrijving for doc in documenten]

        required_informatieobjecttype_omschrijvingen = [
            iot.informatieobjecttype_omschrijving
            for iot in self.camunda_start_process.processinformatieobject_set.all()
        ]
        for iot_omschrijving in required_informatieobjecttype_omschrijvingen:
            if iot_omschrijving not in iots:
                raise serializers.ValidationError(
                    _(
                        "A INFORMATIEOBJECT with INFORMATIEOBJECTTYPE description `{omschrijving}` is required."
                    ).format(omschrijving=iot_omschrijving)
                )
        return documenten

    def validate_rollen(self, rollen):
        rollen = get_rollen(zaak=self.zaakcontext.zaak)
        # Validate that rollen in zaak match required rollen
        required_rt_omsch_betr_type = {}
        for rt in self.camunda_start_process.processrol_set.all():
            if rt.roltype_omschrijving not in required_rt_omsch_betr_type:
                required_rt_omsch_betr_type[rt.roltype_omschrijving] = [
                    rt.betrokkene_type
                ]
            else:
                required_rt_omsch_betr_type[rt.roltype_omschrijving].append(
                    rt.betrokkene_type
                )

        all_roltypen_urls = {
            rt.url: rt for rt in get_roltypen(self.zaakcontext.zaaktype)
        }
        # resolve roltype of rollen
        roltypen_omschrijvingen = {}
        for rol in rollen:
            rol.roltype = all_roltypen_urls[rol.roltype]
            if rol.roltype.omschrijving not in roltypen_omschrijvingen:
                roltypen_omschrijvingen[rol.roltype.omschrijving] = [rol]

        found_rt_omsch_betr_type = {}
        for rol in rollen:
            if rol.roltype.omschrijving not in roltypen_omschrijvingen:
                found_rt_omsch_betr_type[rol.roltype.omschrijving] = [
                    rol.betrokkene_type
                ]
            else:
                found_rt_omsch_betr_type[rol.roltype.omschrijving].append(
                    rol.betrokkene_type
                )

        # First check if roltype omschrijving of rol matches required roltype omschrijving
        # AND then check if betrokkene type of rol matches the required roltype.
        for omschrijving, betrokkene_typen in required_rt_omsch_betr_type.items():
            if found_betrokkene_typen := found_rt_omsch_betr_type.get(omschrijving):
                for betrokkene_type in betrokkene_typen:
                    if betrokkene_type not in found_betrokkene_typen:
                        raise serializers.ValidationError(
                            _(
                                "Betrokkene type of ROL with ROLTYPE omschrijving `{omschrijving}` does not match required betrokkene type `{bt}`"
                            ).format(omschrijving=omschrijving, bt=betrokkene_type)
                        )
            else:
                raise serializers.ValidationError(
                    _(
                        "Required ROLTYPE omschrijving `{omschrijving}` not found in ROLlen related to ZAAK.."
                    ).format(omschrijving=omschrijving)
                )
        return rollen

    def validate_zaakeigenschappen(self, zaakeigenschappen):
        # Validate that zaakeigenschappen related to zaak match required zaakeigenschappen.
        zaakeigenschappen = get_zaak_eigenschappen(self.zaakcontext.zaak)
        required_zaakeigenschapnamen = [
            ei.eigenschapnaam
            for ei in self.camunda_start_process.processeigenschap_set.all()
        ]
        found_zaakeigenschapnamen = [zei["naam"] for zei in zaakeigenschappen]
        for required_zei in required_zaakeigenschapnamen:
            if required_zei not in found_zaakeigenschapnamen:
                raise serializers.ValidationError(
                    _(
                        "A ZAAKEIGENCHAP with eigenschapnaam `{eigenschapnaam}` is required."
                    ).format(eigenschapnaam=required_zei)
                )
        return zaakeigenschappen

    def on_task_submission(self) -> None:
        """
        On task submission do nothing but assert that serializer is valid.

        """
        assert self.is_valid(), "Serializer must be valid"

    def get_process_variables(self) -> Dict[str, Union[List, str]]:
        """
        Get the required BPMN process variables for the BPMN.

        """
        return {
            "eigenschappen": self.validated_data["zaakeigenschappen"],
            "bijlagen": self.validated_data["bijlagen"],
            "rollen": self.validated_data["rollen"],
            **{ei.naam: ei.waarde for ei in self.validated_data["zaakeigenschappen"]},
            **{
                f"bijlage{i+1}": bijlage
                for i, bijlage in enumerate(self.validated_data["bijlagen"])
            },
            **{rol.roltype.omschrijving: rol for rol in self.validated_data["rollen"]},
        }


@dataclass
class StartProcessFormContext(Context):
    bijlagen: List[ProcessInformatieObject]
    rollen: List[ProcessRol]
    zaakeigenschappen: List[ProcessEigenschap]


@usertask_context_serializer
class CamundaZaakProcessContextSerializer(APIModelSerializer):
    bijlagen = ProcessInformatieObjectSerializer(
        many=True,
        required=False,
        help_text=_("These INFORMATIEOBJECTen need to be set to start the process."),
    )
    rollen = ProcessRolSerializer(
        many=True,
        required=False,
        help_text=_("These ROLlen need to be set to start the process."),
    )
    zaakeigenschappen = ProcessEigenschapSerializer(
        many=True,
        required=False,
        help_text=_("These ZAAKEIGENSCHAPpen need to be set to start the process."),
    )

    class Meta:
        model = StartProcessFormContext
        fields = (
            "bijlagen",
            "rollen",
            "zaakeigenschappen",
        )


@register(
    "zac:startProcessForm",
    CamundaZaakProcessContextSerializer,
    ConfigureZaakProcessSerializer,
)
def get_zaak_start_process_form_context(task: Task) -> StartProcessFormContext:
    zaak_context = get_zaak_context(task, require_zaaktype=True, require_documents=True)
    camunda_start_process = get_object_or_404(
        CamundaStartProcess,
        zaaktype_catalogus=zaak_context.zaaktype.catalogus,
        zaaktype_identificatie=zaak_context.zaaktype.identificatie,
    )
    bijlagen = get_required_process_informatie_objecten(
        zaak_context, camunda_start_process
    )
    rollen = get_required_rollen(zaak_context, camunda_start_process)
    zaakeigenschappen = get_required_zaakeigenschappen(
        zaak_context, camunda_start_process
    )
    return StartProcessFormContext(
        zaakeigenschappen=zaakeigenschappen,
        bijlagen=bijlagen,
        rollen=rollen,
    )
