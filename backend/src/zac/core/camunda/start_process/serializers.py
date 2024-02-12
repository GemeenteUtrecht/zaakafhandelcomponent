from copy import deepcopy
from dataclasses import dataclass
from functools import partial
from typing import Dict, List, Union

from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.api_models.zaken import Rol, ZaakEigenschap
from zgw_consumers.drf.serializers import APIModelSerializer

from zac.api.context import get_zaak_context
from zac.camunda.data import Task
from zac.camunda.user_tasks import Context, register, usertask_context_serializer
from zac.contrib.objects.services import fetch_start_camunda_process_form_for_zaaktype
from zac.core.api.serializers import (
    EigenschapSerializer,
    InformatieObjectTypeSerializer,
    RolTypeSerializer,
    ZaakEigenschapSerializer,
)
from zac.core.services import get_rollen, get_roltypen, get_zaakeigenschappen
from zac.elasticsearch.searches import count_by_iot_in_zaak

from .data import (
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


class CreatedProcessInstanceSerializer(serializers.Serializer):
    instance_id = serializers.UUIDField(
        help_text=_("The UUID of the process instance."),
        read_only=True,
    )
    instance_url = serializers.URLField(
        help_text=_("The URL of the process instance."), read_only=True
    )


class ProcessEigenschapChoiceSerializer(APIModelSerializer):
    class Meta:
        model = ProcessEigenschapChoice
        fields = ("label", "value")


class ProcessEigenschapSerializer(APIModelSerializer):
    choices = ProcessEigenschapChoiceSerializer(
        many=True,
        required=True,
        help_text=_("Possible choices related to the EIGENSCHAP."),
    )
    eigenschap = EigenschapSerializer(
        required=True, help_text=_("The EIGENSCHAP related to the ZAAKEIGENSCHAP.")
    )

    class Meta:
        model = ProcessEigenschap
        fields = ("choices", "eigenschap", "label", "default", "required", "order")


class ProcessInformatieObjectSerializer(APIModelSerializer):
    already_uploaded_informatieobjecten = serializers.IntegerField(
        help_text=_("Count of already uploaded documents of INFORMATIEOBJECTTYPE."),
        default=0,
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
            "order",
        )


class ProcessRolSerializer(APIModelSerializer):
    roltype = RolTypeSerializer(
        _("roltype"), required=True, help_text=_("The ROLTYPE related to the ROL.")
    )

    class Meta:
        model = ProcessRol
        fields = ("betrokkene_type", "label", "roltype", "required", "order")


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


class GetCurrentZaakInformation:
    def set_context(self, serializer_field):
        zaakcontext = serializer_field.parent.zaakcontext
        zaakcontext.zaak.zaaktype = zaakcontext.zaaktype
        self.field_name = serializer_field.field_name
        self.mapping = {
            "bijlagen": partial(count_by_iot_in_zaak, zaakcontext.zaak.url),
            "rollen": partial(get_rollen, zaakcontext.zaak),
            "zaakeigenschappen": partial(get_zaakeigenschappen, zaakcontext.zaak),
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
                self.context["task"], require_zaaktype=True
            )
        return self._zaakcontext

    @property
    def camunda_start_process(self):
        if not hasattr(self, "_camunda_start_process"):
            form = fetch_start_camunda_process_form_for_zaaktype(
                self.zaakcontext.zaaktype
            )
            if not form:
                raise serializers.ValidationError(
                    _(
                        "No camunda start process form is found for zaaktype with `identificatie`: `{zaaktype_identificatie}` within catalogus `{zaaktype_catalogus}`."
                    ).format(
                        zaaktype_identificatie=self.zaakcontext.zaaktype.identificatie,
                        zaaktype_catalogus=self.zaakcontext.zaaktype.catalogus,
                    )
                )
            self._camunda_start_process = form
        return self._camunda_start_process

    def validate_bijlagen(self, iots_found: List[str]) -> List[Document]:
        required_iots_omschrijvingen = [
            iot.informatieobjecttype_omschrijving
            for iot in self.camunda_start_process.process_informatie_objecten
            if iot.required
        ]
        for iot in required_iots_omschrijvingen:
            if iot not in iots_found:
                raise serializers.ValidationError(
                    _(
                        "A INFORMATIEOBJECT with INFORMATIEOBJECTTYPE `omschrijving`: `{omschrijving}` is required."
                    ).format(omschrijving=iot)
                )
        return iots_found

    def validate_rollen(self, rollen) -> List[Rol]:
        # Validate that rollen in zaak match required rollen
        # Get required rollen, map their omschrijving to their
        # betrokkene_type to validate that both are set appropriately.
        required_rt_omsch_betr_type = {}
        for process_rol in self.camunda_start_process.process_rollen:
            if process_rol.required:
                if process_rol.roltype_omschrijving not in required_rt_omsch_betr_type:
                    required_rt_omsch_betr_type[process_rol.roltype_omschrijving] = [
                        process_rol.betrokkene_type
                    ]
                else:
                    required_rt_omsch_betr_type[
                        process_rol.roltype_omschrijving
                    ].append(process_rol.betrokkene_type)

        # Get all roltypen and map their URL to themselves.
        all_roltypen_urls = {
            rt.url: rt for rt in get_roltypen(self.zaakcontext.zaaktype)
        }
        # Resolve the roltype of rollen and map roltype omschrijving to rol betrokkene type(n).
        found_rt_omsch_betr_type = {}
        for rol in rollen:
            roltype = all_roltypen_urls[rol.roltype]
            if (omschrijving := roltype.omschrijving) not in found_rt_omsch_betr_type:
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
                                "`betrokkene_type` of ROL with ROLTYPE `omschrijving`: `{omschrijving}` does not match required `betrokkene_type`: `{bt}`."
                            ).format(omschrijving=omschrijving, bt=betrokkene_type)
                        )
            else:
                raise serializers.ValidationError(
                    _(
                        "Required ROLTYPE `omschrijving`: `{omschrijving}` not found in ROLlen related to ZAAK."
                    ).format(omschrijving=omschrijving)
                )
        return rollen

    def validate_zaakeigenschappen(self, zaakeigenschappen) -> List[ZaakEigenschap]:
        # Validate that zaakeigenschappen related to zaak match required zaakeigenschappen.
        required_zaakeigenschappen = {
            ei.eigenschapnaam: ei
            for ei in get_required_zaakeigenschappen(
                self.zaakcontext, self.camunda_start_process
            )
            if ei.required
        }
        if required_zaakeigenschappen:
            if len(required_zaakeigenschappen) > 1:
                raise serializers.ValidationError(
                    _("ZAAKEIGENSCHAPpen with `namen`: `{namen}` are required.").format(
                        namen=list(required_zaakeigenschappen.keys())
                    )
                )
            raise serializers.ValidationError(
                _("A ZAAKEIGENSCHAP with `naam`: `{naam}` is required.").format(
                    naam=list(required_zaakeigenschappen.keys())[0]
                )
            )

        return zaakeigenschappen

    def on_task_submission(self) -> None:
        """
        On task submission assert serializer is valid
        and serialize fields for camunda.

        """
        assert self.is_valid(), "Serializer must be valid"

        self.validated_data["zaakeigenschappen"] = [
            deepcopy(data)
            for data in ZaakEigenschapSerializer(
                self.validated_data["zaakeigenschappen"], many=True
            ).data
        ]  # ordereddict unpacking into dict to shut up django_camunda.utils.serialize_variable

    def get_process_variables(self) -> Dict[str, Union[List, str]]:
        """
        Get the required BPMN process variables for the BPMN.

        """

        eigenschappen = {
            ei["eigenschap"]["naam"]: ei["waarde"]
            for ei in self.validated_data["zaakeigenschappen"]
        }
        return {
            "eigenschappen": [
                {"naam": naam, "waarde": waarde}
                for naam, waarde in eigenschappen.items()
            ],
            **eigenschappen,
            **{
                rol.get_roltype_omschrijving(): {
                    "betrokkeneType": rol.betrokkene_type,
                    "betrokkeneIdentificatie": rol.betrokkene_identificatie,
                    "name": rol.get_name(),
                    "omschrijving": rol.get_roltype_omschrijving(),
                    "roltoelichting": rol.get_roltype_omschrijving(),
                    "identificatie": rol.get_identificatie(),
                }
                for rol in self.validated_data["rollen"]
            },
        }


@register(
    "zac:startProcessForm",
    CamundaZaakProcessContextSerializer,
    ConfigureZaakProcessSerializer,
)
def get_zaak_start_process_form_context(task: Task) -> StartProcessFormContext:
    zaak_context = get_zaak_context(task, require_zaaktype=True)
    camunda_start_process = fetch_start_camunda_process_form_for_zaaktype(
        zaak_context.zaaktype
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
