import logging
from copy import deepcopy
from dataclasses import dataclass
from functools import partial
from typing import Dict, List, Union

from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.api_models.zaken import Rol, ZaakEigenschap

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
from zac.tests.compat import APIModelSerializer

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

logger = logging.getLogger(__name__)


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
        dataclass = ProcessEigenschapChoice
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
        dataclass = ProcessEigenschap
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
        dataclass = ProcessInformatieObject
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
        dataclass = ProcessRol
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
        dataclass = StartProcessFormContext
        fields = (
            "benodigde_bijlagen",
            "benodigde_rollen",
            "benodigde_zaakeigenschappen",
        )


class ConfigureZaakProcessSerializer(serializers.Serializer):
    """
    Serializer for configuring Camunda start process data for a ZAAK.

    This version assumes write-only usage (PUT), so it dynamically populates
    bijlagen (Dict[str, int]), rollen (List[Rol]), and zaakeigenschappen
    (List[ZaakEigenschap]) at validation time instead of relying on
    HiddenField defaults.
    """

    bijlagen = serializers.DictField(
        child=serializers.IntegerField(),
        required=False,
        help_text=_("Mapping of INFORMATIEOBJECTTYPE omschrijvingen to counts."),
    )
    rollen = serializers.ListField(
        required=False,
        help_text=_("Existing rollen related to the zaak."),
    )
    zaakeigenschappen = serializers.ListField(
        required=False,
        help_text=_("Existing zaakeigenschappen related to the zaak."),
    )

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
                        "No camunda start process form is found for zaaktype with "
                        "`identificatie`: `{zaaktype_identificatie}` within catalogus `{zaaktype_catalogus}`."
                    ).format(
                        zaaktype_identificatie=self.zaakcontext.zaaktype.identificatie,
                        zaaktype_catalogus=self.zaakcontext.zaaktype.catalogus,
                    )
                )
            self._camunda_start_process = form
        return self._camunda_start_process

    def _get_current_zaak_information(self) -> Dict[str, Union[Dict, List]]:
        """
        Dynamically resolve all current zaak information at validation time.
        """
        from zac.core.services import get_rollen, get_zaakeigenschappen
        from zac.elasticsearch.searches import count_by_iot_in_zaak

        zaak = self.zaakcontext.zaak
        zaak.zaaktype = self.zaakcontext.zaaktype

        return {
            "bijlagen": count_by_iot_in_zaak(zaak.url) or {},
            "rollen": get_rollen(zaak) or [],
            "zaakeigenschappen": get_zaakeigenschappen(zaak) or [],
        }

    def validate(self, attrs):
        """
        Inject dynamically fetched zaak information before running field validation.
        """
        current = self._get_current_zaak_information()

        attrs["bijlagen"] = current["bijlagen"]
        attrs["rollen"] = current["rollen"]
        attrs["zaakeigenschappen"] = current["zaakeigenschappen"]

        # run subfield validations manually
        self.validate_bijlagen(attrs["bijlagen"])
        self.validate_rollen(attrs["rollen"])
        self.validate_zaakeigenschappen(attrs["zaakeigenschappen"])

        return attrs

    def validate_bijlagen(self, iots_found: Dict[str, int]) -> Dict[str, int]:
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
        required_rt_omsch_betr_type = {}
        for process_rol in self.camunda_start_process.process_rollen:
            if process_rol.required:
                required_rt_omsch_betr_type.setdefault(
                    process_rol.roltype_omschrijving, []
                ).append(process_rol.betrokkene_type)

        all_roltypen_urls = {
            rt.url: rt for rt in get_roltypen(self.zaakcontext.zaaktype)
        }

        found_rt_omsch_betr_type = {}
        for rol in rollen:
            roltype = all_roltypen_urls[rol.roltype]
            found_rt_omsch_betr_type.setdefault(roltype.omschrijving, []).append(
                rol.betrokkene_type
            )

        for omschrijving, betrokkene_typen in required_rt_omsch_betr_type.items():
            found_betrokkene_typen = found_rt_omsch_betr_type.get(omschrijving)
            if not found_betrokkene_typen:
                raise serializers.ValidationError(
                    _(
                        "Required ROLTYPE `omschrijving`: `{omschrijving}` not found in ROLlen related to ZAAK."
                    ).format(omschrijving=omschrijving)
                )
            for betrokkene_type in betrokkene_typen:
                if betrokkene_type not in found_betrokkene_typen:
                    raise serializers.ValidationError(
                        _(
                            "`betrokkene_type` of ROL with ROLTYPE `omschrijving`: `{omschrijving}` "
                            "does not match required `betrokkene_type`: `{bt}`."
                        ).format(omschrijving=omschrijving, bt=betrokkene_type)
                    )
        return rollen

    def validate_zaakeigenschappen(self, zaakeigenschappen) -> List[ZaakEigenschap]:
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
        assert self.is_valid(), "Serializer must be valid"
        self.validated_data["zaakeigenschappen"] = [
            deepcopy(data)
            for data in ZaakEigenschapSerializer(
                self.validated_data["zaakeigenschappen"], many=True
            ).data
        ]

    def get_process_variables(self) -> Dict[str, Union[List, str]]:
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
