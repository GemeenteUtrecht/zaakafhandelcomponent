from typing import Dict, List, Union

from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from zgw_consumers.api_models.constants import RolTypes

from zac.api.context import ZaakContext, get_zaak_context
from zac.camunda.data import Task
from zac.camunda.user_tasks import register, usertask_context_serializer
from zac.core.api.serializers import (
    EigenschapSerializer,
    InformatieObjectTypeSerializer,
    RolSerializer,
    RolTypeSerializer,
)
from zac.core.services import (
    fetch_documents,
    get_documenten,
    get_eigenschappen,
    get_rollen,
    get_roltypen,
    get_zaak_eigenschappen,
    resolve_documenten_informatieobjecttypen,
)

from .models import (
    CamundaStartProcessForm,
    ProcessEigenschap,
    ProcessEigenschapChoice,
    ProcessInformatieObject,
    ProcessRol,
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
    default = serializers.CharField(
        _("default"),
        required=False,
        allow_blank=True,
        help_text=_("Default value of the ZAAKEIGENSCHAP."),
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
        child=serializers.URLField,
        required=False,
        help_text=_("The URLs of already uploaded "),
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
    betrokkene_type = serializers.CharField(
        _("betrokkene type"),
        required=True,
        choices=RolTypes,
        help_text=_("Betrokkene type of the ROL."),
    )
    default = serializers.CharField(
        _("default"),
        required=False,
        allow_blank=True,
        help_text=_("Default value given to the ROL betrokkene."),
    )

    class Meta:
        model = ProcessRol
        fields = ("roltype", "label", "value", "betrokkene_type", "default")


@usertask_context_serializer
class CamundaZaakProcessContextSerializer(serializers.Serializer):
    zaakeigenschappen = ProcessEigenschapSerializer(
        many=True,
        required=False,
        help_text=_("These ZAAKEIGENSCHAPpen need to be set to start the process."),
    )
    informatieobjecten = ProcessInformatieObjectSerializer(
        many=True,
        required=False,
        help_text=_("These INFORMATIEOBJECTen need to be set to start the process."),
    )
    rollen = ProcessRolSerializer(
        many=True,
        required=False,
        help_text=_("These ROLlen need to be set to start the process."),
    )


def get_required_process_informatie_objecten(
    zaak_context: ZaakContext, camunda_start_process_form: CamundaStartProcessForm
) -> List[ProcessInformatieObjectSerializer]:
    # Get all documents that are already uploaded and add them to
    # already_uploaded_informatieobjecten if their
    # informatieobjecttype.omschrijving matches.
    zaak_context.documents = resolve_documenten_informatieobjecttypen(
        zaak_context.documents
    )
    ziot_omschrijvingen_to_doc_url_map = {}
    for doc in zaak_context.documents:
        if (
            omschrijving := doc.informatieobjecttype.omschrijving
            not in ziot_omschrijvingen_to_doc_url_map
        ):
            ziot_omschrijvingen_to_doc_url_map[omschrijving] = [doc.url]
        else:
            ziot_omschrijvingen_to_doc_url_map[omschrijving].append(doc.url)

    # Get all required process informatie objecten from CamundaStartProcessForm
    pi_objecten = camunda_start_process_form.processinformatieobject_set.all()
    required_process_informatie_objecten = []
    for piobject in pi_objecten:
        if (
            omschrijving := piobject.informatieobjecttype_omschrijving
            in ziot_omschrijvingen_to_doc_url_map.keys()
        ):
            piobject.already_uploaded_informatieobjecten = (
                ziot_omschrijvingen_to_doc_url_map[omschrijving]
            )

        required_process_informatie_objecten.append(piobject)
    return required_process_informatie_objecten


def get_required_rollen(
    zaak_context: ZaakContext, camunda_start_process_form: CamundaStartProcessForm
) -> List[ProcessRolSerializer]:
    # Get all rollen that are already created and check if any of them
    # match the required rollen. Drop those that are already created.
    rollen = get_rollen(zaak_context.zaak)
    roltypen = {roltype.url: roltype for roltype in get_roltypen(zaak_context.zaaktype)}
    # resolve roltypen to rollen
    already_set_roltype = []
    for rol in rollen:
        rol.roltype = roltypen[rol.roltype]
        already_set_roltype.append(rol.roltype.omschrijving)

    # Get all required rollen from CamundaStartProcessForm
    process_rollen = camunda_start_process_form.processrol_set.all()
    required_process_rollen = []
    omschrijving_to_roltypen_map = {
        roltype.omschrijving: roltype for url, roltype in roltypen.items()
    }
    for process_rol in process_rollen:
        if process_rol.roltype_omschrijving in already_set_roltype:
            continue
        process_rol.roltype = omschrijving_to_roltypen_map[
            process_rol.roltype_omschrijving
        ]
        required_process_rollen.append(process_rol)
    return required_process_rollen


def get_required_zaakeigenschappen(
    zaak_context: ZaakContext, camunda_start_process_form: CamundaStartProcessForm
) -> List[ProcessEigenschap]:
    # Get all zaakeigenschappen and check if any of them match the
    # required zaakeigenschappen. Drop those that are already created.
    zaakeigenschappen = [
        zei.eigenschap.eigenschapnaam
        for zei in get_zaak_eigenschappen(zaak_context.zaak)
    ]
    eigenschappen = {
        ei.eigenschaapnaam: ei for ei in get_eigenschappen(zaak_context.zaaktype)
    }
    required_eigenschappen = camunda_start_process_form.processeigenschap_set.all()
    required_process_eigenschappen = []
    for ei in required_eigenschappen:
        if ei.eigenschapnaam in zaakeigenschappen.keys():
            continue

        ei.eigenschap = eigenschappen[ei.eigenschapnaam]
        required_process_eigenschappen.append(ei)

    return required_process_eigenschappen


def get_camunda_start_process_form_from_zaakcontext(
    zaak_context: ZaakContext,
) -> CamundaStartProcessForm:
    # Get related CamundaStartProcessForm
    camunda_start_process_form = CamundaStartProcessForm.objects.filter(
        zaaktype_catalogus=zaak_context.zaaktype.catalogus,
        zaaktype_identificatie=zaak_context.zaaktype.identificatie,
    )

    # Make sure it exists
    if not camunda_start_process_form.exists():
        raise RuntimeError(
            "Please create a camunda start process form for this zaaktype first."
        )
    else:
        camunda_start_process_form = camunda_start_process_form[0]
    return camunda_start_process_form


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
    bijlagen = serializers.ListField(child=serializers.URLField())
    zaakeigenschappen = ZaakProcessEigenschapSerializer(many=True)
    rollen = RolSerializer(many=True)

    @property
    def zaakcontext(self):
        if not hasattr(self, "_zaakcontext"):
            self._zaakcontext = get_zaak_context(
                self.context["task"], require_zaaktype=True, require_documents=True
            )
        return self._zaakcontext

    @property
    def camunda_start_process_form(self):
        if not hasattr(self, "_camunda_start_process_form"):
            try:
                camunda_start_process_form = CamundaStartProcessForm.objects.get(
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
            self._camunda_start_process_form = camunda_start_process_form
        return self._camunda_start_process_form

    def validate_bijlagen(self, bijlagen):
        # Validate that zaakeigenschappen related to zaak match required zaakeigenschappen.
        documenten, gone = get_documenten(self.zaakcontext.zaak)
        documenten = resolve_documenten_informatieobjecttypen(documenten)
        iots = [doc.informatieobjecttype.omschrijving for doc in documenten]

        required_informatieobjecttype_omschrijvingen = [
            iot.informatieobjecttype_omschrijving
            for iot in self.camunda_start_process_form.processinformatieobject_set.all()
        ]
        for iot_omschrijving in required_informatieobjecttype_omschrijvingen:
            if iot_omschrijving not in iots:
                raise serializers.ValidationError(
                    _(
                        "A INFORMATIEOBJECT with INFORMATIEOBJECTTYPE description `{omschrijving}` is required."
                    ).format(omschrijving=iot_omschrijving)
                )
        return documenten

    def validate_zaakeigenschappen(self, zaakeigenschappen):
        # Validate that zaakeigenschappen related to zaak match required zaakeigenschappen.
        zaakeigenschappen = get_zaak_eigenschappen(self.zaakcontext.zaak)
        required_zaakeigenschapnamen = [
            ei.eigenschapnaam
            for ei in self.camunda_start_process_form.processeigenschap_set.all()
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

    def validate_rollen(self, rollen):
        rollen = get_rollen(zaak=self.zaakcontext.zaak)
        # Validate that rollen in zaak match required rollen
        required_rt_omsch_betr_type = {}
        for rt in self.camunda_start_process_form.processrol_set.all():
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


@register(
    "zac:StartProcessForm",
    CamundaZaakProcessContextSerializer,
    ConfigureZaakProcessSerializer,
)
def get_zaak_start_process_form_context(task: Task) -> Dict:
    zaak_context = get_zaak_context(task, require_zaaktype=True, require_documents=True)
    camunda_start_process_form = get_camunda_start_process_form_from_zaakcontext(
        zaak_context
    )
    informatieobjecten = get_required_process_informatie_objecten(
        zaak_context, camunda_start_process_form
    )
    rollen = get_required_rollen(zaak_context, camunda_start_process_form)
    zaakeigenschappen = get_required_zaakeigenschappen(
        zaak_context, camunda_start_process_form
    )
    return {
        "zaakeigenschappen": zaakeigenschappen,
        "informatieobjecten": informatieobjecten,
        "rollen": rollen,
    }