from typing import Dict, List, Union

from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from zac.api.context import ZaakContext, get_zaak_context
from zac.core.services import (
    get_eigenschappen,
    get_rollen,
    get_roltypen,
    get_zaak_eigenschappen,
    resolve_documenten_informatieobjecttypen,
)
from zgw.models.zrc import Zaak
from zac.camunda.data import Task
from zac.core.api.serializers import (
    EigenschapSerializer,
    InformatieObjectTypeSerializer,
    RolTypeSerializer,
)

from ..models import (
    CamundaStartProcessForm,
    ProcessEigenschap,
    ProcessEigenschapChoice,
    ProcessInformatieObject,
    ProcessRol,
)
from ..user_tasks import register, usertask_context_serializer


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
        fields = ("choices", "eigenschap", "label", "value")


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
        required=True, help_text=_("The ROLTYPE related to the ROL.")
    )

    class Meta:
        model = ProcessRol
        fields = ("roltype", "label", "value")


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


class ConfigureZaakProcessSerializer(serializers.Serializer):
    def validate(self, attrs):
        task = self.context["task"]

    def get_zaak_from_context(self):
        zaak_context = get_zaak_context(self.context["task"])
        return zaak_context.zaak

    def on_task_submission(self) -> None:
        """
        On task submission do nothing.

        """
        pass

    def get_process_variables(self) -> Dict[str, Union[List, str]]:
        """
        Get the required BPMN process variables for the BPMN.

        """
        pass


@register("zac:StartProcessForm", CamundaZaakProcessContextSerializer)
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
