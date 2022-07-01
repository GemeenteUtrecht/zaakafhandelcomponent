from dataclasses import dataclass
from functools import partial
from typing import Dict, List, Union

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Prefetch
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework.generics import get_object_or_404
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.api_models.zaken import Rol, ZaakEigenschap
from zgw_consumers.drf.serializers import APIModelSerializer

from zac.api.context import get_zaak_context
from zac.camunda.data import Task
from zac.camunda.user_tasks import Context, register, usertask_context_serializer
from zac.core.api.serializers import (
    EigenschapSerializer,
    InformatieObjectTypeSerializer,
    ReadRolSerializer,
    RolTypeSerializer,
    ZaakEigenschapSerializer,
)
from zac.core.services import (
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
    ProcessRolChoice,
)
from .utils import (
    get_required_process_informatie_objecten,
    get_required_rollen,
    get_required_zaakeigenschappen,
)


class CreatedProcessInstanceSerializer(serializers.Serializer):
    instance_id = serializers.UUIDField(
        help_text=_("The UUID of the process instance."),
        read_only=True,
    )
    instance_url = serializers.URLField(
        help_text=_("The URL of the process instance."), read_only=True
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
        fields = ("choices", "eigenschap", "label", "default")


class ProcessInformatieObjectSerializer(serializers.ModelSerializer):
    already_uploaded_informatieobjecten = serializers.ListField(
        child=serializers.URLField(),
        required=False,
        help_text=_("URL-references of already uploaded documents."),
    )
    informatieobjecttype = InformatieObjectTypeSerializer(
        required=True,
        help_text=_("The INFORMATIEOBJECTTYPE related to the ZAAKINFORMATIEOBJECT."),
        allow_null=True,
    )

    class Meta:
        model = ProcessInformatieObject
        fields = (
            "already_uploaded_informatieobjecten",
            "allow_multiple",
            "informatieobjecttype",
            "label",
            "required",
        )


class ProcessRolChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProcessRolChoice
        fields = ("label", "value")


class ProcessRolSerializer(serializers.ModelSerializer):
    choices = ProcessRolChoiceSerializer(
        many=True,
        required=False,
        help_text=_("Possible choices related to the ROL."),
        source="processrolchoice_set",
    )
    roltype = RolTypeSerializer(
        _("roltype"), required=True, help_text=_("The ROLTYPE related to the ROL.")
    )

    class Meta:
        model = ProcessRol
        fields = (
            "betrokkene_type",
            "choices",
            "label",
            "roltype",
        )


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


class GetCurrentZaakInformation:
    def set_context(self, serializer_field):
        zaakcontext = serializer_field.parent.zaakcontext
        zaakcontext.zaak.zaaktype = zaakcontext.zaaktype
        self.field_name = serializer_field.field_name
        self.mapping = {
            "bijlagen": partial(
                resolve_documenten_informatieobjecttypen, zaakcontext.documents
            ),
            "rollen": partial(get_rollen, zaakcontext.zaak),
            "zaakeigenschappen": partial(get_zaak_eigenschappen, zaakcontext.zaak),
        }

    def __call__(self):
        return self.mapping[self.field_name]()


class ConfigureZaakProcessSerializer(serializers.Serializer):
    bijlagen = serializers.HiddenField(default=GetCurrentZaakInformation())
    rollen = serializers.HiddenField(default=GetCurrentZaakInformation())
    zaakeigenschappen = serializers.HiddenField(default=GetCurrentZaakInformation())

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
                self._camunda_start_process = (
                    CamundaStartProcess.objects.prefetch_related(
                        "processinformatieobject_set",
                        Prefetch(
                            "processrol_set",
                            queryset=ProcessRol.objects.prefetch_related(
                                "processrolchoice_set"
                            ).all(),
                        ),
                        Prefetch(
                            "processeigenschap_set",
                            queryset=ProcessEigenschap.objects.prefetch_related(
                                "processeigenschapchoice_set"
                            ).all(),
                        ),
                    ).get(
                        zaaktype_catalogus=self.zaakcontext.zaaktype.catalogus,
                        zaaktype_identificatie=self.zaakcontext.zaaktype.identificatie,
                    )
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
        return self._camunda_start_process

    def validate_bijlagen(self, bijlagen) -> List[Document]:
        # Validate that bijlagen related to zaak match required document(types).
        iots = [doc.informatieobjecttype.omschrijving for doc in bijlagen]

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
        return bijlagen

    def validate_rollen(self, rollen) -> List[Rol]:
        # Validate that rollen in zaak match required rollen
        # Get required rollen, map their omschrijving to their
        # betrokkene_type to validate that both are set appropriately.
        required_rt_omsch_betr_type = {}
        for process_rol in self.camunda_start_process.processrol_set.all():
            if process_rol.roltype_omschrijving not in required_rt_omsch_betr_type:
                required_rt_omsch_betr_type[process_rol.roltype_omschrijving] = [
                    process_rol.betrokkene_type
                ]
            else:
                required_rt_omsch_betr_type[process_rol.roltype_omschrijving].append(
                    process_rol.betrokkene_type
                )

        # Get all roltypen and map their URL to themselves.
        all_roltypen_urls = {
            rt.url: rt for rt in get_roltypen(self.zaakcontext.zaaktype)
        }
        # Resolve the roltype of rollen and map roltype omschrijving to rol betrokkene type(n).
        found_rt_omsch_betr_type = {}
        for rol in rollen:
            rol.roltype = all_roltypen_urls[rol.roltype]
            if (
                omschrijving := rol.roltype.omschrijving
            ) not in found_rt_omsch_betr_type:
                found_rt_omsch_betr_type[omschrijving] = [rol.betrokkene_type]
            else:
                found_rt_omsch_betr_type[omschrijving].append(rol.betrokkene_type)

        # First check if roltype omschrijving of rol matches required roltype omschrijving
        # of process_rol. Then check if betrokkene_type of rol matches the
        # betrokkene_type of the required process_rol with that roltype omschrijving.
        for omschrijving, betrokkene_typen in required_rt_omsch_betr_type.items():
            if found_betrokkene_typen := found_rt_omsch_betr_type.get(omschrijving):
                for betrokkene_type in betrokkene_typen:
                    if betrokkene_type not in found_betrokkene_typen:
                        raise serializers.ValidationError(
                            _(
                                "`betrokkene_type` of ROL with ROLTYPE omschrijving `{omschrijving}` does not match required betrokkene_type `{bt}`"
                            ).format(omschrijving=omschrijving, bt=betrokkene_type)
                        )
            else:
                raise serializers.ValidationError(
                    _(
                        "Required ROLTYPE omschrijving `{omschrijving}` not found in ROLlen related to ZAAK."
                    ).format(omschrijving=omschrijving)
                )
        return rollen

    def validate_zaakeigenschappen(self, zaakeigenschappen) -> List[ZaakEigenschap]:
        # Validate that zaakeigenschappen related to zaak match required zaakeigenschappen.
        required_zaakeigenschappen = {
            ei.eigenschapnaam: {
                pec.label: pec.value for pec in ei.processeigenschapchoice_set.all()
            }
            for ei in self.camunda_start_process.processeigenschap_set.all()
        }
        found_zaakeigenschapnaamwaarden = {
            zei.naam: zei.waarde for zei in zaakeigenschappen
        }
        for required_zei in required_zaakeigenschappen.keys():
            if required_zei not in found_zaakeigenschapnaamwaarden:
                raise serializers.ValidationError(
                    _(
                        "A ZAAKEIGENCHAP with `naam`: `{eigenschapnaam}` is required."
                    ).format(eigenschapnaam=required_zei)
                )
            else:
                if (
                    found_zaakeigenschapnaamwaarden[required_zei]
                    not in required_zaakeigenschappen[required_zei].values()
                ):
                    raise serializers.ValidationError(
                        _(
                            "ZAAKEIGENCHAP with `naam`: `{eigenschapnaam}`, needs to have a `waarde` chosen from: {choices}."
                        ).format(
                            eigenschapnaam=required_zei,
                            choices=sorted(
                                list(required_zaakeigenschappen[required_zei].keys())
                            ),
                        )
                    )
        return zaakeigenschappen

    def on_task_submission(self) -> None:
        """
        On task submission assert serializer is valid
        and serialize fields for camunda.

        """
        assert self.is_valid(), "Serializer must be valid"

        self.validated_data["bijlagen"] = [
            doc.url for doc in self.validated_data["bijlagen"]
        ]
        self.validated_data["zaakeigenschappen"] = [
            {**data}
            for data in ZaakEigenschapSerializer(
                self.validated_data["zaakeigenschappen"], many=True
            ).data
        ]  # ordereddict unpacking into dict to shut up django_camunda.utils.serialize_variable
        self.validated_data["rollen"] = [
            {**data}
            for data in ReadRolSerializer(self.validated_data["rollen"], many=True).data
        ]  # ordereddict unpacking into dict to shut up django_camunda.utils.serialize_variable

    def get_process_variables(self) -> Dict[str, Union[List, str]]:
        """
        Get the required BPMN process variables for the BPMN.

        """

        return {
            "bijlagen": self.validated_data["bijlagen"],
            "eigenschappen": self.validated_data["zaakeigenschappen"],
            "rollen": self.validated_data["rollen"],
            **{
                ei["eigenschap"]["naam"]: ei["waarde"]
                for ei in self.validated_data["zaakeigenschappen"]
            },
            **{
                f"bijlage{i+1}": bijlage
                for i, bijlage in enumerate(self.validated_data["bijlagen"])
            },
            **{rol["roltoelichting"]: rol for rol in self.validated_data["rollen"]},
        }


@dataclass
class StartProcessFormContext(Context):
    benodigde_bijlagen: List[ProcessInformatieObject]
    benodigde_rollen: List[ProcessRol]
    benodigde_zaakeigenschappen: List[ProcessEigenschap]


@usertask_context_serializer
class CamundaZaakProcessContextSerializer(APIModelSerializer):
    benodigde_bijlagen = ProcessInformatieObjectSerializer(
        many=True,
        required=False,
        help_text=_("These INFORMATIEOBJECTen need to be set to start the process."),
    )
    benodigde_rollen = ProcessRolSerializer(
        many=True,
        required=False,
        help_text=_("These ROLlen need to be set to start the process."),
    )
    benodigde_zaakeigenschappen = ProcessEigenschapSerializer(
        many=True,
        required=False,
        help_text=_("These ZAAKEIGENSCHAPpen need to be set to start the process."),
    )

    class Meta:
        model = StartProcessFormContext
        fields = (
            "benodigde_bijlagen",
            "benodigde_rollen",
            "benodigde_zaakeigenschappen",
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
        benodigde_bijlagen=bijlagen,
        benodigde_rollen=rollen,
        benodigde_zaakeigenschappen=zaakeigenschappen,
    )
