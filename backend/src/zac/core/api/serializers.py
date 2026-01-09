import json
import logging
import pathlib
from datetime import datetime
from decimal import ROUND_05UP
from typing import Dict, Optional

from django.conf import settings
from django.core.validators import RegexValidator
from django.template.defaultfilters import filesizeformat
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext as _

from furl import furl
from requests.exceptions import HTTPError
from rest_framework import serializers
from rest_framework.utils import formatting
from zds_client.client import ClientError
from zgw_consumers.api_models.catalogi import (
    EIGENSCHAP_FORMATEN,
    Catalogus,
    Eigenschap,
    EigenschapSpecificatie,
    InformatieObjectType,
    ResultaatType,
    RolType,
    StatusType,
    ZaakType,
)
from zgw_consumers.api_models.constants import (
    AardRelatieChoices,
    RolOmschrijving,
    RolTypes,
    VertrouwelijkheidsAanduidingen,
)
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.api_models.zaken import Resultaat, Status, ZaakEigenschap

from zac.accounts.api.serializers import AtomicPermissionSerializer
from zac.accounts.models import User
from zac.api.polymorphism import (
    GroupPolymorphicSerializer,
    PolymorphicSerializer,
    SerializerCls,
)
from zac.api.proxy import ProxySerializer
from zac.camunda.api.utils import (
    get_bptl_app_id_variable,
    get_incidents_for_process_instance,
)
from zac.camunda.constants import AssigneeTypeChoices
from zac.camunda.variable_instances import get_camunda_variable_instances
from zac.contrib.dowc.constants import DocFileTypes
from zac.contrib.dowc.fields import DowcUrlField
from zac.contrib.objects.services import (
    fetch_start_camunda_process_form_for_zaaktype,
    fetch_zaaktypeattributen_objects_for_zaaktype,
)
from zac.core.camunda.utils import resolve_assignee
from zac.core.fields import DownloadDocumentURLField
from zac.core.models import MetaObjectTypesConfig
from zac.core.rollen import Rol
from zac.core.services import (
    fetch_object,
    fetch_objecttype,
    fetch_objecttypes,
    fetch_rol,
    fetch_zaaktype,
    find_zaak,
    get_document,
    get_informatieobjecttypen_for_zaak,
    get_informatieobjecttypen_for_zaaktype,
    get_rollen,
    get_roltypen,
    get_statustypen,
    get_zaak,
    get_zaakobjecten,
    get_zaaktypen,
    relate_object_to_zaak,
)
from zac.core.utils import build_absolute_url
from zac.elasticsearch.searches import search_informatieobjects
from zac.tests.compat import APIModelSerializer
from zgw.models.zrc import Zaak

from ..zaakobjecten import ZaakObjectGroup
from .data import VertrouwelijkheidsAanduidingData
from .fields import NullableJsonField
from .permissions import CanForceEditClosedZaak
from .utils import (
    CSMultipleChoiceField,
    TypeChoices,
    ValidExpandChoices,
    ValidFieldChoices,
)
from .validators import EigenschapKeuzeWaardeValidator, ZaakFileValidator

logger = logging.getLogger(__name__)


class InformatieObjectTypeSerializer(APIModelSerializer):
    class Meta:
        model = InformatieObjectType
        fields = (
            "url",
            "omschrijving",
        )


class GetZaakDocumentSerializer(APIModelSerializer):
    delete_url = serializers.SerializerMethodField(
        help_text=_(
            "The URL required to save edits and delete the DOWC object related to the INFORMATIEOBJECT."
        )
    )
    current_user_is_editing = serializers.SerializerMethodField(
        help_text=_(
            "Boolean flag to indicate if requesting user is editing current INFORMATIEOBJECT."
        )
    )
    download_url = DownloadDocumentURLField()
    informatieobjecttype = InformatieObjectTypeSerializer(
        help_text=_("The INFORMATIEOBJECTTYPE related to the ZAAKINFORMATIEOBJECT.")
    )
    last_edited_date = serializers.SerializerMethodField(
        help_text=_("Shows last edited datetime.")
    )
    locked_by = serializers.SerializerMethodField(
        help_text=_("Email of user that locked document.")
    )
    read_url = DowcUrlField(
        purpose=DocFileTypes.read,
        help_text=_(
            "URL to read INFORMATIEOBJECT. Opens the appropriate Microsoft Office application."
        ),
    )
    vertrouwelijkheidaanduiding = serializers.CharField(
        source="get_vertrouwelijkheidaanduiding_display",
        help_text=_("Vertrouwelijkheidaanduiding of INFORMATIEOBJECT."),
    )
    write_url = DowcUrlField(
        purpose=DocFileTypes.write,
        allow_blank=True,
        help_text=_(
            "URL to write INFORMATIEOBJECT. Opens the appropriate Microsoft Office application."
        ),
    )

    class Meta:
        model = Document
        fields = (
            "auteur",
            "beschrijving",
            "bestandsnaam",
            "bestandsomvang",
            "current_user_is_editing",
            "delete_url",
            "download_url",
            "identificatie",
            "informatieobjecttype",
            "last_edited_date",
            "locked",
            "locked_by",
            "read_url",
            "titel",
            "url",
            "versie",
            "vertrouwelijkheidaanduiding",
            "write_url",
        )
        extra_kwargs = {
            "bestandsomvang": {
                "help_text": _("File size in bytes of INFORMATIEOBJECT."),
            }
        }

    def get_delete_url(self, obj) -> str:
        dowc_obj = self.context.get("open_documenten", {}).get(obj.url, None)
        if dowc_obj and dowc_obj.locked_by == self.context["request"].user.email:
            return reverse(
                "dowc:patch-destroy-doc", kwargs={"dowc_uuid": dowc_obj.uuid}
            )
        return ""

    def get_current_user_is_editing(self, obj) -> bool:
        dowc_obj = self.context.get("open_documenten", {}).get(obj.url, None)
        if dowc_obj and dowc_obj.locked_by == self.context["request"].user.email:
            return True
        return False

    def get_locked_by(self, obj) -> str:
        if obj.locked and (
            open_dowc := self.context.get("open_documenten", {}).get(obj.url, None)
        ):
            return open_dowc.locked_by
        return ""

    def get_last_edited_date(self, obj) -> Optional[datetime]:
        return self.context.get("editing_history", {}).get(obj.url)


class AddZaakDocumentSerializer(serializers.Serializer):
    beschrijving = serializers.CharField(
        required=False, help_text=_("Description of the DOCUMENT")
    )
    file = serializers.FileField(
        required=False,
        use_url=False,
        help_text=_("Content of the DOCUMENT. Mutually exclusive with `url` attribute"),
        validators=(ZaakFileValidator(),),
    )
    informatieobjecttype = serializers.URLField(
        required=False,
        help_text=_(
            "URL-reference of INFORMATIEOBJECTTYPE in CATALOGI API. Required if `file` is provided"
        ),
    )
    url = serializers.URLField(
        required=False,
        help_text=_(
            "URL-reference of DOCUMENT in DOCUMENTEN API. Mutually exclusive with `file` attribute"
        ),
    )
    zaak = serializers.URLField(
        required=True,
        help_text=_("URL-reference of the ZAAK in ZAKEN API"),
        allow_blank=False,
    )

    def validate(self, data):
        zaak = data.get("zaak")
        document_url = data.get("url")
        file = data.get("file")

        if document_url and file:
            raise serializers.ValidationError(
                "'url' and 'file' are mutually exclusive and can't be provided together."
            )

        if not document_url and not file:
            raise serializers.ValidationError(
                "Either 'url' or 'file' should be provided."
            )

        if file:
            bestandsnaam = file.name
            informatieobjecttype_url = data.get("informatieobjecttype")
            if not informatieobjecttype_url:
                raise serializers.ValidationError(
                    "'informatieobjecttype' is required when 'file' is provided"
                )
        else:
            try:
                document = get_document(document_url)
            except (ClientError, HTTPError) as exc:
                raise serializers.ValidationError(detail={"url": exc.args[0]})

            bestandsnaam = document.bestandsnaam
            informatieobjecttype_url = document.informatieobjecttype

        if not bestandsnaam:
            raise serializers.ValidationError(
                _("A `file` or `document` needs a `bestandsnaam`.")
            )

        if (
            search_informatieobjects(
                bestandsnaam=bestandsnaam, zaak=zaak, size=0, return_search=True
            ).count()
            > 0
        ):
            raise serializers.ValidationError(
                _(
                    "`bestandsnaam`: `{bestandsnaam}` already exists. Please choose a unique `bestandsnaam`."
                ).format(bestandsnaam=bestandsnaam)
            )

        # check that zaaktype relates to iotype
        informatieobjecttypen = get_informatieobjecttypen_for_zaak(zaak)
        present = any(
            iot for iot in informatieobjecttypen if iot.url == informatieobjecttype_url
        )
        if not present:
            raise serializers.ValidationError("Invalid informatieobjecttype given.")

        return data


class UpdateZaakDocumentSerializer(serializers.Serializer):
    beschrijving = serializers.CharField(required=False)
    file = serializers.FileField(
        required=False, use_url=False, validators=(ZaakFileValidator(),)
    )
    reden = serializers.CharField(
        help_text=_("Reason for the edit, used in audit trail."),
        required=True,
        allow_null=True,
    )
    url = serializers.URLField(
        help_text=_("URL-reference of DOCUMENT"), allow_blank=False
    )
    vertrouwelijkheidaanduiding = serializers.ChoiceField(
        choices=VertrouwelijkheidsAanduidingen.choices,
        help_text=_("Vertrouwelijkheidaanduiding of DOCUMENT."),
        required=False,
    )
    zaak = serializers.URLField(
        required=True,
        help_text=_("URL-reference of the ZAAK."),
        allow_blank=False,
    )
    bestandsnaam = serializers.CharField(
        help_text=_("Filename without extension."),
        required=False,
    )
    informatieobjecttype = serializers.URLField(
        help_text=_("URL-reference to INFORMATIEOBJECTTYPE."),
        required=False,
    )

    def validate(self, data):
        data = super().validate(data)
        document_url = data.get("url")
        zaak = get_zaak(zaak_url=data["zaak"])

        if file := data.get("file"):
            bestandsnaam = file.name

        if document := search_informatieobjects(
            zaak=zaak.url, size=1, urls=[document_url]
        ):
            if bestandsnaam := data.get("bestandsnaam"):
                bestandsnaam = pathlib.Path(bestandsnaam).stem
                bestandsnaam = bestandsnaam + "".join(
                    pathlib.Path(document[0].bestandsnaam).suffixes
                )
                data["bestandsnaam"] = bestandsnaam
                data["titel"] = bestandsnaam
        else:
            raise serializers.ValidationError(
                _("The document is unrelated to {zaak}.").format(
                    zaak=zaak.identificatie
                )
            )

        if (
            bestandsnaam
            and search_informatieobjects(
                zaak=zaak.url, size=0, bestandsnaam=bestandsnaam, return_search=True
            ).count()
            > 0
        ):
            raise serializers.ValidationError(
                _(
                    "`bestandsnaam`: `{bestandsnaam}` already exists. Please choose a unique `bestandsnaam`."
                ).format(bestandsnaam=bestandsnaam)
            )

        if iot := data.get("informatieobjecttype"):
            zt = fetch_zaaktype(zaak.zaaktype)
            iots = get_informatieobjecttypen_for_zaaktype(zt)
            if iot not in [_iot.url for _iot in iots]:
                raise serializers.ValidationError(
                    _(
                        "INFORMATIEOBJECTTYPE `{iot}` is not related to ZAAKTYPE `{zt}`."
                    ).format(iot=iot, zt=zt.omschrijving)
                )

        return data


class DocumentInfoSerializer(serializers.Serializer):
    document_type = serializers.CharField(source="informatieobjecttype.omschrijving")
    titel = serializers.CharField(
        help_text=_("Title of the INFORMATIEOBJECT. Includes the file extension.")
    )
    vertrouwelijkheidaanduiding = serializers.CharField(
        source="get_vertrouwelijkheidaanduiding_display"
    )
    bestandsgrootte = serializers.SerializerMethodField()

    read_url = DowcUrlField(
        purpose=DocFileTypes.read,
        help_text=_(
            "URL to read INFORMATIEOBJECT. Opens the appropriate Microsoft Office application."
        ),
    )
    download_url = DownloadDocumentURLField()

    def get_bestandsgrootte(self, obj):
        return filesizeformat(obj.bestandsomvang)


class ExpandParamSerializer(serializers.Serializer):
    fields = CSMultipleChoiceField(
        choices=ValidExpandChoices.choices,
        required=False,
    )


class ExtraInfoUpSerializer(serializers.Serializer):
    burgerservicenummer = serializers.CharField(
        allow_blank=False,
        required=True,
        max_length=9,
        validators=[
            RegexValidator(
                regex="^[0-9]{9}$",
                message="Een BSN heeft 9 cijfers.",
                code="invalid",
            )
        ],
    )

    doelbinding = serializers.CharField(
        allow_blank=False,
        required=True,
    )

    fields = CSMultipleChoiceField(
        choices=ValidFieldChoices.choices,
        required=True,
        strict=True,
    )


class ExtraInfoSubjectSerializer(serializers.Serializer):
    geboortedatum = serializers.CharField()
    geboorteland = serializers.CharField()
    kinderen = serializers.ListField()
    verblijfplaats = serializers.DictField()
    partners = serializers.ListField()


class AddZaakRelationSerializer(serializers.Serializer):
    bijdragezaak = serializers.URLField(
        required=True,
        help_text=_("URL-reference to the ZAAK that is to the main ZAAK."),
    )
    aard_relatie = serializers.ChoiceField(
        required=True,
        choices=AardRelatieChoices,
        help_text=_(
            "The nature of the relationship between the main ZAAK and the related ZAAK."
        ),
    )
    hoofdzaak = serializers.URLField(
        required=True,
        help_text=_("URL-reference to the main ZAAK in the ZAKEN API."),
    )
    aard_relatie_omgekeerde_richting = serializers.ChoiceField(
        required=True,
        choices=AardRelatieChoices,
        help_text=_("The nature of the reverse relationship."),
    )

    def validate(self, data):
        """
        Check that the main zaak and the relation are not the same nor have the same relationship.

        """
        if data["bijdragezaak"] == data["hoofdzaak"]:
            raise serializers.ValidationError(
                _("ZAAKen cannot be related to themselves.")
            )
        if data["aard_relatie"] == data["aard_relatie_omgekeerde_richting"]:
            raise serializers.ValidationError(
                _("The nature of the ZAAK-relations cannot be the same.")
            )
        return data


class DeleteZaakRelationSerializer(serializers.Serializer):
    bijdragezaak = serializers.URLField(
        required=True,
        help_text=_("URL-reference to the ZAAK that is to the main ZAAK."),
    )
    hoofdzaak = serializers.URLField(
        required=True,
        help_text=_("URL-reference to the main ZAAK in the ZAKEN API."),
    )


class CreateZaakDetailsSerializer(serializers.Serializer):
    omschrijving = serializers.CharField(
        required=True, help_text=_("A short summary of the ZAAK."), max_length=80
    )
    toelichting = serializers.CharField(
        help_text=_("A comment on the ZAAK."), default="", allow_blank=True
    )


class CreateZaakSerializer(serializers.Serializer):
    organisatie_rsin = serializers.CharField(
        help_text=_(
            "The RSIN of the organization that created the ZAAK. This has to be a valid `RSIN` of 9 digits and comply to https://nl.wikipedia.org/wiki/Burgerservicenummer#11-proef."
        ),
        default="002220647",
        max_length=9,
        validators=[
            RegexValidator(
                regex="^[0-9]{9}$",
                message="A RSIN has 9 digits.",
                code="invalid",
            )
        ],
    )
    zaaktype_identificatie = serializers.CharField(
        required=True,
        help_text=_("`identificatie` of ZAAKTYPE."),
    )
    zaaktype_catalogus = serializers.URLField(
        required=True,
        help_text=_("URL-reference to the CATALOGUS of ZAAKTYPE."),
    )
    zaaktype = serializers.HiddenField(default="")
    zaak_details = CreateZaakDetailsSerializer(
        help_text=_("Relevant details pertaining to the ZAAK.")
    )
    object = serializers.URLField(
        help_text=_("URL-reference to OBJECT which is to be related to ZAAK."),
        required=False,
        allow_blank=False,
    )
    object_type = serializers.CharField(
        help_text=_(
            "Type of OBJECT as required by Open Zaak. Defaults to `overige`. Don't change unless you know what you are doing. Only inserted into BPMN if OBJECT URL is also given."
        ),
        default="overige",
    )
    object_type_overige = serializers.CharField(
        help_text=_(
            "Description of OBJECT as required by Open Zaak. Defaults to `name` of OBJECT TYPE related to OBJECT. Only inserted into BPMN if OBJECT URL is also given."
        ),
        default=None,
    )
    start_related_business_process = serializers.BooleanField(
        help_text=_(
            "Automagically start related business process if it exists once ZAAK is created."
        ),
        default=True,
    )

    def validate_object(self, object: str) -> Dict:
        try:
            object = fetch_object(object)
        except ClientError as exc:
            raise serializers.ValidationError(
                _(
                    "Fetching OBJECT with URL: `{object}` raised a Client Error with detail: `{detail}`.".format(
                        object=object, detail=exc.args[0]["detail"]
                    )
                )
            )
        return object

    def validate(self, data):
        validated_data = super().validate(data)
        zaak_details = CreateZaakDetailsSerializer(data=validated_data["zaak_details"])
        zaak_details.is_valid(raise_exception=True)
        validated_data["zaak_details"] = json.loads(
            json.dumps(zaak_details.data)
        )  # django_camunda.utils can't handle ordereddict
        if object := validated_data.pop("object", None):
            validated_data["object_type_overige"] = (
                validated_data["object_type_overige"] or object["type"]["name"]
            )
            validated_data["object_url"] = object["url"]
        else:
            # remove object type (overige)
            validated_data.pop("object_type", None)
            validated_data.pop("object_type_overige", None)

        zt_identificatie = validated_data["zaaktype_identificatie"]
        zt_catalogus = validated_data["zaaktype_catalogus"]
        zaaktypen = get_zaaktypen(
            catalogus=zt_catalogus,
            identificatie=zt_identificatie,
            request=self.context["request"],
        )
        if not zaaktypen:
            raise serializers.ValidationError(
                _(
                    "ZAAKTYPE with `identificatie`: `{zt_identificatie}` can not be found in `{zt_catalogus}` or user does not have permission."
                ).format(zt_identificatie=zt_identificatie, zt_catalogus=zt_catalogus)
            )
        max_date = max([zt.versiedatum for zt in zaaktypen])
        zaaktype = [zt for zt in zaaktypen if zt.versiedatum == max_date][0]
        validated_data["zaaktype"] = zaaktype.url
        validated_data["zaaktype_omschrijving"] = zaaktype.omschrijving

        # If roltypes contain an initiator include `initiator` in validated_data
        roltypen = [
            rt
            for rt in get_roltypen(zaaktype)
            if rt.omschrijving_generiek == RolOmschrijving.initiator
        ]
        if roltypen:
            validated_data["initiator"] = (
                f"{AssigneeTypeChoices.user}:{self.context['request'].user}"
            )

        return validated_data

    def to_internal_value(self, data):
        serialized_data = {
            **super().to_internal_value(data),
            **get_bptl_app_id_variable(),
        }
        organisatie_rsin = serialized_data.pop("organisatie_rsin")
        serialized_data["organisatieRSIN"] = organisatie_rsin
        return serialized_data


class ZaakSerializer(serializers.Serializer):
    identificatie = serializers.CharField(required=True)
    bronorganisatie = serializers.CharField(required=True)
    url = serializers.URLField(required=True)


class ZaakTypeSerializer(APIModelSerializer):
    class Meta:
        model = ZaakType
        fields = (
            "url",
            "catalogus",
            "omschrijving",
            "versiedatum",
        )


class ResultaatTypeSerializer(APIModelSerializer):
    class Meta:
        model = ResultaatType
        fields = ("url", "omschrijving")


class ResultaatSerializer(APIModelSerializer):
    resultaattype = ResultaatTypeSerializer()

    class Meta:
        model = Resultaat
        fields = ("url", "resultaattype", "toelichting")


class FetchZaakDetailUrlSerializer(serializers.Serializer):
    zaak_detail_url = serializers.SerializerMethodField(
        help_text=_("URL of the ZAAK detail page in the zaakafhandelcomponent."),
        read_only=True,
    )

    def get_zaak_detail_url(self, zaak: Zaak) -> str:
        path = furl(settings.UI_ROOT_URL).path.segments + [
            "zaken",
            zaak.bronorganisatie,
            zaak.identificatie,
        ]
        return build_absolute_url(path, request=self.context["request"])


class ZaakDetailSerializer(APIModelSerializer):
    zaaktype = ZaakTypeSerializer(help_text=_("Expanded ZAAKTYPE of ZAAK."))
    deadline = serializers.DateField(read_only=True)
    deadline_progress = serializers.FloatField(
        label=_("Progress towards deadline"),
        read_only=True,
        help_text=_(
            "Value between 0-100, representing a percentage. 100 means the deadline "
            "has been reached or exceeded."
        ),
    )
    resultaat = ResultaatSerializer()
    zaakgeometrie = serializers.JSONField(
        required=False,
        help_text=_("GeoJSON which represents the coordinates of the ZAAK"),
    )
    kan_geforceerd_bijwerken = serializers.SerializerMethodField(
        help_text=_("A boolean flag whether a user can force edit the ZAAK or not."),
    )
    has_process = serializers.SerializerMethodField(
        help_text=_("A boolean flag whether the ZAAK has a process or not.")
    )
    is_static = serializers.SerializerMethodField(
        help_text=_("A boolean flag whether the ZAAK is stationary or not.")
    )
    is_configured = serializers.SerializerMethodField(
        help_text=_(
            "A boolean flag whether the ZAAK has already been configured or not."
        )
    )

    class Meta:
        model = Zaak
        fields = (
            "url",
            "identificatie",
            "bronorganisatie",
            "zaaktype",
            "omschrijving",
            "toelichting",
            "registratiedatum",
            "startdatum",
            "einddatum",
            "einddatum_gepland",
            "vertrouwelijkheidaanduiding",
            "zaakgeometrie",
            "deadline",
            "deadline_progress",
            "resultaat",
            "kan_geforceerd_bijwerken",
            "has_process",
            "is_static",
            "is_configured",
        )

    def get_kan_geforceerd_bijwerken(self, obj) -> bool:
        return CanForceEditClosedZaak().check_for_any_permission(
            self.context["request"], obj
        )

    def get_has_process(self, obj) -> bool:
        process_instances = self.context["process_instances"]

        # Filter out the process instance that started the zaak
        spawned_process_instances = [
            pi
            for pi in process_instances.values()
            if pi.definition.key != settings.CREATE_ZAAK_PROCESS_DEFINITION_KEY
        ]
        if spawned_process_instances:
            return True

        # It might be possible that a process is still being spawned.
        # Check if the process SHOULD spawn child processes.

        parent_process_instance = [
            pi
            for pi in process_instances.values()
            if pi.definition.key == settings.CREATE_ZAAK_PROCESS_DEFINITION_KEY
        ]
        if not parent_process_instance:
            return False

        if len(parent_process_instance) > 1:
            logger.warning(
                _(
                    "Something went wrong. A ZAAK shouldn't be spawned by more than 1 parent."
                )
            )
        parent_process_instance = parent_process_instance[0]

        # Make sure the process doesn't have incidents yet:
        incidents = get_incidents_for_process_instance(parent_process_instance.id)
        if incidents:
            logger.error("Something went wrong. An incident was reported in Camunda.")

        # Make sure the parent process has startRelatedBusinessProcess.
        if var := bool(
            get_camunda_variable_instances(
                {
                    "processInstanceIdIn": list(process_instances.keys()),
                    "variableName": "startRelatedBusinessProcess",
                }
            )
        ):
            # Make sure the zaaktype of the zaak has a start_camunda_process_form
            if var and self.context["camunda_form"]:
                return True
        return False

    def get_is_static(self, obj) -> bool:
        form = fetch_start_camunda_process_form_for_zaaktype(obj.zaaktype)
        return not form

    def get_is_configured(self, obj) -> bool:
        process_instances = self.context["process_instances"]
        if process_instances:
            return bool(
                get_camunda_variable_instances(
                    {
                        "processInstanceIdIn": list(process_instances.keys()),
                        "variableName": "isConfigured",
                    }
                )
            )
        return False


class UpdateZaakDetailSerializer(APIModelSerializer):
    reden = serializers.CharField(
        required=False,
        help_text=_(
            "Reason for the edit, used in audit trail. Required when `vertrouwelijkheidaanduiding` is changed"
        ),
    )
    vertrouwelijkheidaanduiding = serializers.ChoiceField(
        VertrouwelijkheidsAanduidingen.choices,
        required=False,
        help_text=_("The confidentiality level of the ZAAK."),
    )
    zaakgeometrie = NullableJsonField(
        required=False,
        allow_null=True,
        help_text=_("GeoJSON which represents the coordinates of the ZAAK"),
    )

    class Meta:
        model = Zaak
        fields = (
            "einddatum",
            "einddatum_gepland",
            "omschrijving",
            "reden",
            "toelichting",
            "vertrouwelijkheidaanduiding",
            "zaakgeometrie",
        )
        extra_kwargs = {
            "einddatum": {
                "required": False,
            },
            "einddatum_gepland": {
                "required": False,
            },
            "omschrijving": {
                "required": False,
                "allow_blank": True,
            },
            "toelichting": {
                "required": False,
                "allow_blank": True,
            },
        }

    def validate(self, attrs):
        validated_data = super().validate(attrs)

        zaak = self.context["zaak"]
        vertrouwelijkheidaanduiding = validated_data.get("vertrouwelijkheidaanduiding")
        reden = validated_data.get("reden")

        if (
            not reden
            and vertrouwelijkheidaanduiding
            and vertrouwelijkheidaanduiding != zaak.vertrouwelijkheidaanduiding
        ):
            raise serializers.ValidationError(
                "'reden' is required when 'vertrouwelijkheidaanduiding' is changed"
            )

        return validated_data


class StatusTypeSerializer(APIModelSerializer):
    class Meta:
        model = StatusType
        fields = (
            "url",
            "omschrijving",
            "omschrijving_generiek",
            "statustekst",
            "volgnummer",
            "is_eindstatus",
        )
        extra_kwargs = {
            "omschrijving": {"read_only": True},
            "omschrijving_generiek": {"read_only": True},
            "statustekst": {"read_only": True},
            "volgnummer": {"read_only": True},
            "is_eindstatus": {"read_only": True},
        }

    def validate_url(self, url: str) -> str:
        zaaktype = self.context["zaaktype"]
        if not isinstance(zaaktype, ZaakType):
            zaaktype = fetch_zaaktype(zaaktype)

        statustypen = get_statustypen(zaaktype)
        if not url in [st.url for st in statustypen]:
            raise serializers.ValidationError("Invalid STATUSTYPE URL given.")
        return url


class ZaakStatusSerializer(APIModelSerializer):
    statustype = StatusTypeSerializer()

    class Meta:
        model = Status
        fields = (
            "url",
            "datum_status_gezet",
            "statustoelichting",
            "statustype",
        )
        extra_kwargs = {
            "url": {"read_only": True},
            "datum_status_gezet": {"read_only": True},
        }


class EigenschapSpecificatieSerializer(APIModelSerializer):
    waardenverzameling = serializers.ListField(child=serializers.CharField())
    formaat = serializers.ChoiceField(
        choices=list(EIGENSCHAP_FORMATEN.keys()),
        label=_("data type"),
    )

    class Meta:
        model = EigenschapSpecificatie
        fields = (
            "groep",
            "formaat",
            "lengte",
            "kardinaliteit",
            "waardenverzameling",
        )


class EigenschapSerializer(APIModelSerializer):
    specificatie = EigenschapSpecificatieSerializer(label=_("EIGENSCHAP definition"))

    class Meta:
        model = Eigenschap
        fields = (
            "url",
            "naam",
            "toelichting",
            "specificatie",
        )


class CharValueSerializer(APIModelSerializer):
    waarde = serializers.CharField(
        label=_("EIGENSCHAP value"),
        source="get_waarde",
        validators=(EigenschapKeuzeWaardeValidator(),),
    )

    class Meta:
        model = ZaakEigenschap
        fields = ("waarde",)


class NumberValueSerializer(APIModelSerializer):
    # TODO: Ideally this should be dynamic based on eigenschapsspecificatie
    waarde = serializers.DecimalField(
        label=_("EIGENSCHAP value"),
        source="get_waarde",
        max_digits=100,
        decimal_places=2,
        rounding=ROUND_05UP,
        validators=(EigenschapKeuzeWaardeValidator(),),
    )

    class Meta:
        model = ZaakEigenschap
        fields = ("waarde",)


class DateValueSerializer(APIModelSerializer):
    waarde = serializers.DateField(
        label=_("EIGENSCHAP value"),
        source="get_waarde",
        validators=(EigenschapKeuzeWaardeValidator(),),
    )

    class Meta:
        model = ZaakEigenschap
        fields = ("waarde",)


class DateTimeValueSerializer(APIModelSerializer):
    waarde = serializers.DateTimeField(
        label=_("EIGENSCHAP value"),
        source="get_waarde",
        validators=(EigenschapKeuzeWaardeValidator(),),
    )

    class Meta:
        model = ZaakEigenschap
        fields = ("waarde",)


class ZaakEigenschapSerializer(PolymorphicSerializer, APIModelSerializer):
    serializer_mapping = {
        "tekst": CharValueSerializer,
        "getal": NumberValueSerializer,
        "datum": DateValueSerializer,
        "datum_tijd": DateTimeValueSerializer,
    }
    discriminator_field = "formaat"

    formaat = serializers.ChoiceField(
        label=_("Data type of the value"),
        read_only=True,
        source="eigenschap.specificatie.formaat",
        choices=list(serializer_mapping.keys()),
        help_text=_(
            "Matches `eigenschap.specificatie.formaat` - used as API schema "
            "discriminator."
        ),
    )
    eigenschap = EigenschapSerializer(read_only=True)

    class Meta:
        model = ZaakEigenschap
        fields = (
            "url",
            "formaat",
            "eigenschap",
        )
        extra_kwargs = {
            "url": {"read_only": True},
        }


class CreateZaakEigenschapSerializer(serializers.Serializer):
    naam = serializers.CharField(
        help_text=_(
            "Name of EIGENSCHAP. Must match EIGENSCHAP name as defined in CATALOGI API."
        )
    )
    waarde = serializers.CharField(
        help_text=_(
            "Value of ZAAKEIGENSCHAP. Must be able to be formatted as defined by the EIGENSCHAP spec."
        ),
        validators=(EigenschapKeuzeWaardeValidator(),),
    )
    zaak_url = serializers.URLField(help_text=_("URL-reference to ZAAK."))


class UpdateZaakEigenschapWaardeSerializer(serializers.Serializer):
    waarde = serializers.CharField(
        help_text=_(
            "Value of ZAAKEIGENSCHAP. Must be formatted as defined by the EIGENSCHAP spec."
        )
    )

    def validate_waarde(self, waarde):
        zaak = get_zaak(zaak_url=self.instance.zaak_url)
        zaaktype = fetch_zaaktype(zaak.zaaktype)
        zt_attrs = {
            data["naam"]: data
            for data in fetch_zaaktypeattributen_objects_for_zaaktype(zaaktype=zaaktype)
        }
        if self.instance.naam in zt_attrs:
            if enum := zt_attrs[self.instance.naam].get("enum"):
                if waarde not in enum:
                    raise serializers.ValidationError(
                        _(
                            "Invalid `waarde`: `{waarde}`. Zaakeigenschap with `naam`: `{naam}` must take value from: `{choices}`.".format(
                                waarde=waarde, naam=self.instance.naam, choices=enum
                            )
                        )
                    )
        return waarde


class RelatedZaakDetailSerializer(APIModelSerializer):
    status = ZaakStatusSerializer(help_text=_("Expanded STATUS of ZAAK."))
    zaaktype = ZaakTypeSerializer(help_text=_("Expanded ZAAKTYPE of ZAAK."))
    resultaat = ResultaatSerializer(help_text=_("Expanded RESULTAAT of ZAAK."))

    class Meta:
        model = Zaak
        fields = (
            "bronorganisatie",
            "identificatie",
            "omschrijving",
            "resultaat",
            "status",
            "zaaktype",
            "url",
        )


class RelatedZaakSerializer(serializers.Serializer):
    aard_relatie = serializers.CharField(
        help_text=_("Short description of the nature of the relationship.")
    )
    zaak = RelatedZaakDetailSerializer()


class RolTypeSerializer(APIModelSerializer):
    class Meta:
        model = RolType
        fields = ("url", "omschrijving", "omschrijving_generiek")


class ReadRolSerializer(APIModelSerializer):
    name = serializers.CharField(source="get_name")
    identificatie = serializers.CharField(source="get_identificatie")
    betrokkene_type = serializers.ChoiceField(
        choices=RolTypes,
        help_text=_("Betrokkene type of ROL. Mutually exclusive with `betrokkene`."),
    )
    betrokkene_type_display = serializers.CharField(
        source="get_betrokkene_type_display"
    )
    roltype_omschrijving = serializers.CharField(
        source="get_roltype_omschrijving",
        help_text=_("Description of ROLTYPE related to ROL."),
    )

    class Meta:
        model = Rol
        fields = (
            "url",
            "betrokkene_type",
            "betrokkene_type_display",
            "omschrijving",
            "omschrijving_generiek",
            "roltoelichting",
            "registratiedatum",
            "name",
            "identificatie",
            "roltype_omschrijving",
        )


def betrokkene_identificatie_serializer(serializer_cls: SerializerCls) -> SerializerCls:
    """
    Ensure that the betrokkene_identificatie serializer is wrapped in a serializer.

    The decorator enforces the same label/help_text and meta-information for the API
    schema documentation.
    """

    name = serializer_cls.__name__
    name = name = formatting.remove_trailing_string(name, "Serializer")

    class IdentificatieSerializer(serializers.Serializer):
        betrokkene_identificatie = serializer_cls(
            label=_("Betrokkene identificatie"),
            help_text=_(
                """The `betrokkene_identificatie` of the ROL. 
                The shape of the `betrokkene_identificatie` depends on the `betrokkene_type` of the ROL. 
                Mutually exclusive with `betrokkene`. 
                
                Data validation for `betrokkene_identificatie` is done at the source (in this case: Open Zaak).
                """
            ),
        )

    name = f"{name}TaskDataSerializer"
    return type(name, (IdentificatieSerializer,), {})


class PassDataInternalValue:
    def to_internal_value(self, data: dict):
        extra = super().to_representation(data)
        return {**data, **extra}


@betrokkene_identificatie_serializer
class RolNatuurlijkPersoonSerializer(PassDataInternalValue, ProxySerializer):
    PROXY_SCHEMA_BASE = settings.EXTERNAL_API_SCHEMAS["ZRC_API_SCHEMA"]
    PROXY_SCHEMA_PATH = [
        "components",
        "schemas",
        "RolNatuurlijkPersoon",
    ]


@betrokkene_identificatie_serializer
class RolNietNatuurlijkPersoonSerializer(PassDataInternalValue, ProxySerializer):
    PROXY_SCHEMA_BASE = settings.EXTERNAL_API_SCHEMAS["ZRC_API_SCHEMA"]
    PROXY_SCHEMA_PATH = [
        "components",
        "schemas",
        "RolNietNatuurlijkPersoon",
    ]


@betrokkene_identificatie_serializer
class RolVestigingSerializer(PassDataInternalValue, ProxySerializer):
    PROXY_SCHEMA_BASE = settings.EXTERNAL_API_SCHEMAS["ZRC_API_SCHEMA"]
    PROXY_SCHEMA_PATH = [
        "components",
        "schemas",
        "RolVestiging",
    ]


@betrokkene_identificatie_serializer
class RolOrganisatorischeEenheidSerializer(PassDataInternalValue, ProxySerializer):
    PROXY_SCHEMA_BASE = settings.EXTERNAL_API_SCHEMAS["ZRC_API_SCHEMA"]
    PROXY_SCHEMA_PATH = [
        "components",
        "schemas",
        "RolOrganisatorischeEenheid",
    ]


@betrokkene_identificatie_serializer
class RolMedewerkerSerializer(serializers.Serializer):
    voorletters = serializers.SerializerMethodField(
        help_text=_("Initials of medewerker.")
    )
    achternaam = serializers.SerializerMethodField(
        help_text=_("`last_name` of medewerker.")
    )
    identificatie = serializers.CharField(
        required=True,
        help_text=_("`username` of medewerker."),
    )
    voorvoegsel_achternaam = serializers.CharField(
        default="", help_text=_("Last name prefix of medewerker.")
    )

    def get_identificatie(self, attrs) -> str:
        return f"{AssigneeTypeChoices.user}:{self.context.get('user')}"

    def get_voorletters(self, attrs) -> str:
        user = self.context.get("user")
        voorletters = attrs.get("voorletters", "")
        if user:
            return (
                "".join(
                    [part[0].upper() + "." for part in user.first_name.split()]
                ).strip()
                or voorletters
            )
        return voorletters

    def get_achternaam(self, attrs) -> str:
        user = self.context.get("user")
        achternaam = attrs.get("achternaam", "")
        if user:
            return user.last_name.capitalize() or achternaam
        return achternaam

    def validate(self, data):
        validated_data = super().validate(data)
        user = resolve_assignee(validated_data["identificatie"])
        validated_data["achternaam"] = user.last_name.capitalize()
        validated_data["voorletters"] = "".join(
            [part[0].upper() + "." for part in user.first_name.split()]
        ).strip()
        validated_data["identificatie"] = f"{AssigneeTypeChoices.user}:{user}"
        return validated_data


EmptySerializer = betrokkene_identificatie_serializer(serializers.JSONField)


class RolSerializer(PolymorphicSerializer):
    serializer_mapping = {
        RolTypes.natuurlijk_persoon: RolNatuurlijkPersoonSerializer,
        RolTypes.niet_natuurlijk_persoon: RolNietNatuurlijkPersoonSerializer,
        RolTypes.vestiging: RolVestigingSerializer,
        RolTypes.organisatorische_eenheid: RolOrganisatorischeEenheidSerializer,
        RolTypes.medewerker: RolMedewerkerSerializer,
        "": EmptySerializer,
    }
    discriminator_field = "betrokkene_type"
    betrokkene = serializers.URLField(
        help_text=_(
            "URL-reference to betrokkene of ROL. Mutually exclusive with `betrokkene_type`."
        ),
        default="",
    )
    betrokkene_type = serializers.ChoiceField(
        choices=RolTypes.choices,
        help_text=_("Betrokkene type of ROL. Mutually exclusive with `betrokkene`."),
        allow_blank=True,
    )
    indicatie_machtiging = serializers.ChoiceField(
        choices=["gemachtigde", "machtiginggever"], default="gemachtigde"
    )
    roltoelichting = serializers.CharField(
        help_text=_("Comment related to the ROL."),
        default="",
    )
    roltype = serializers.URLField(
        required=True,
        help_text=_("URL-reference to ROLTYPE of ROL."),
    )
    url = serializers.URLField(
        read_only=True, help_text=_("URL-reference to ROL itself.")
    )
    zaak = serializers.URLField(
        help_text=_("URL-reference to ZAAK of ROL."),
    )
    roltype_omschrijving = serializers.CharField(
        read_only=True,
        help_text=_("Description of ROLTYPE related to ROL."),
        source="get_roltype_omschrijving",
    )

    def validate(self, data):
        data = super().validate(data)
        zaak = get_zaak(zaak_url=data["zaak"])
        zaaktype = fetch_zaaktype(zaak.zaaktype)
        roltypen = {rt.url: rt for rt in get_roltypen(zaaktype)}
        if not (rt := roltypen.get(data["roltype"])):
            raise serializers.ValidationError(
                _("ROLTYPE {rt} is not part of ROLTYPEs for ZAAKTYPE {zt}.").format(
                    rt=data["roltype"], zt=zaaktype.url
                )
            )
        else:
            if rt.omschrijving_generiek == RolOmschrijving.initiator:
                raise serializers.ValidationError(
                    _("ROLTYPE {rt} is an initiator and cannot be changed.").format(
                        rt=data["roltype_omschrijving"]
                    )
                )

        if data.get("betrokkene") and data["betrokkene_type"]:
            raise serializers.ValidationError(
                _("`betrokkene` and `betrokkene_type` are mutually exclusive.")
            )
        if data.get("betrokkene") and data["betrokkene_identificatie"]:
            raise serializers.ValidationError(
                _("`betrokkene` and `betrokkene_identificatie` are mutually exclusive.")
            )

        if not data.get("roltoelichting"):
            data["roltoelichting"] = roltypen[data["roltype"]].omschrijving

        return data


class DestroyRolSerializer(APIModelSerializer):
    url = serializers.URLField(
        required=True, help_text=_("URL-reference to ROL itself.")
    )

    class Meta:
        model = Rol
        fields = ("url",)

    def validate_url(self, url):
        if not (zaak := self.context.get("zaak")):
            raise RuntimeError(
                _("Serializer {name} needs ZAAK in context.").format(name=self.__name__)
            )
        rollen = get_rollen(zaak)

        if not any([rol.url == url for rol in rollen]):
            raise serializers.ValidationError(_("ROL does not belong to ZAAK."))

        rol = fetch_rol(url)
        if (
            rol.omschrijving_generiek
            in [RolOmschrijving.behandelaar, RolOmschrijving.initiator]
        ) and (
            len(
                [
                    _rol
                    for _rol in rollen
                    if _rol.omschrijving_generiek
                    in [RolOmschrijving.behandelaar, RolOmschrijving.initiator]
                ]
            )
            == 1
        ):
            raise serializers.ValidationError(
                _(
                    "A ZAAK always requires at least one ROL with an `omschrijving_generiek` that is a `{behandelaar}` or `{initiator}`."
                ).format(
                    behandelaar=RolOmschrijving.behandelaar,
                    initiator=RolOmschrijving.initiator,
                )
            )

        return url


class ZaakObjectGroupSerializer(APIModelSerializer):
    items = serializers.ListField(
        child=serializers.JSONField(),
        help_text=_(
            "Collection of OBJECTTYPE specific items. "
            "The schema is determined by the upstream API(s). "
            "Each item has `zaakobjectUrl` attribute which is the url of ZAAK-OBJECT "
            "relations in ZAKEN API and should be used to change/delete the relations. "
            "See `zac.core.zaakobjecten` for the available implementations."
        ),
    )

    class Meta:
        model = ZaakObjectGroup
        fields = ("object_type", "label", "items")


class CatalogusSerializer(APIModelSerializer):
    class Meta:
        model = Catalogus
        fields = ("domein", "url")


class ZaakTypeAggregateSerializer(APIModelSerializer):
    catalogus = CatalogusSerializer(help_text=_("CATALOGUS that ZAAKTYPE belongs to."))

    class Meta:
        model = ZaakType
        fields = ("catalogus", "omschrijving", "identificatie", "url")
        extra_kwargs = {
            "url": {
                "help_text": _("URL-reference of the ZAAKTYPE in the CATALOGI API.")
            },
            "omschrijving": {
                "help_text": _(
                    "Description of ZAAKTYPE, used as an aggregator of different versions of ZAAKTYPE."
                )
            },
            "identificatie": {"help_text": _("Unique identificatie in CATALOGI API.")},
        }


class BaseEnumSerializer(serializers.Serializer):
    label = serializers.CharField(help_text=_("The label of the enum choice."))


class StringEnumSerializer(BaseEnumSerializer):
    value = serializers.CharField(
        help_text=_("The value of the enum choice as a `string`.")
    )


class NumberEnumSerializer(BaseEnumSerializer):
    value = serializers.FloatField(
        help_text=_("The value of the enum choice as an `integer` or a `float`.")
    )

    def to_representation(self, instance):
        integer = False
        if type(instance["value"]) == int:
            integer = True

        ret = super().to_representation(instance)
        if integer:
            ret["value"] = int(ret["value"])
        return ret


class EigenschapSpecificatieJsonSerializer(GroupPolymorphicSerializer):
    serializer_mapping = {
        TypeChoices.string: StringEnumSerializer,
        TypeChoices.number: NumberEnumSerializer,
    }
    discriminator_field = "type"
    group_field = "enum"
    group_field_kwargs = {
        "help_text": _("An array of possible values."),
        "required": False,
        "many": True,
    }

    type = serializers.ChoiceField(
        choices=TypeChoices.choices,
        help_text=_("According to JSON schema date values have `string` type."),
    )
    format = serializers.CharField(
        required=False,
        help_text=_(
            "Used to differentiate `date` and `date-time` values from other strings."
        ),
    )
    min_length = serializers.IntegerField(
        required=False, help_text=_("Only for strings.")
    )
    max_length = serializers.IntegerField(
        required=False, help_text=_("Only for strings.")
    )


class SearchEigenschapSerializer(serializers.Serializer):
    name = serializers.CharField(help_text=_("Name of EIGENSCHAP"))
    spec = EigenschapSpecificatieJsonSerializer(
        label=_("property definition"),
        help_text=_("JSON schema-ish specification of related ZAAK-EIGENSCHAP values."),
    )


class VertrouwelijkheidsAanduidingSerializer(APIModelSerializer):
    label = serializers.CharField(help_text=_("Human readable label of classication."))
    value = serializers.CharField(help_text=_("Value of classication."))

    class Meta:
        model = VertrouwelijkheidsAanduidingData
        fields = ("label", "value")


class UserAtomicPermissionSerializer(serializers.ModelSerializer):
    permissions = AtomicPermissionSerializer(
        many=True,
        source="zaak_atomic_permissions",
        help_text=_("Atomic permissions for the ZAAK."),
    )
    full_name = serializers.CharField(source="get_full_name")

    class Meta:
        model = User
        fields = ("username", "permissions", "full_name")


class ObjecttypeProxySerializer(ProxySerializer):
    PROXY_SCHEMA_BASE = settings.EXTERNAL_API_SCHEMAS["OBJECTTYPES_API_SCHEMA"]
    PROXY_SCHEMA = ("/api/v2/objecttypes/", "get")
    PROXY_SCHEMA_PATH = ["components", "schemas", "ObjectType"]


class ObjecttypeVersionProxySerializer(ProxySerializer):
    """
    Filter out `meta` fields please.

    """

    PROXY_SCHEMA_BASE = settings.EXTERNAL_API_SCHEMAS["OBJECTTYPES_API_SCHEMA"]
    PROXY_SCHEMA_PATH = ["components", "schemas", "ObjectVersion"]


class ObjectProxySerializer(ProxySerializer):
    """
    Filter out `meta` fields please.

    """

    PROXY_SCHEMA_BASE = settings.EXTERNAL_API_SCHEMAS["OBJECTS_API_SCHEMA"]
    PROXY_SCHEMA_PATH = ["components", "schemas", "Object"]

    stringRepresentation = serializers.CharField(
        required=True,
        allow_blank=True,
        help_text=_(
            "Returns a string representation based on `stringRepresentatie` in objecttype labels."
        ),
    )


class PaginatedObjectProxySerializer(ProxySerializer):
    PROXY_SCHEMA_BASE = settings.EXTERNAL_API_SCHEMAS["OBJECTS_API_SCHEMA"]
    PROXY_SCHEMA_PATH = ["components", "schemas", "PaginatedObjectList"]
    results = ObjectProxySerializer(many=True)


class ObjectFilterProxySerializer(ProxySerializer):
    PROXY_SCHEMA_BASE = settings.EXTERNAL_API_SCHEMAS["OBJECTS_API_SCHEMA"]
    PROXY_SCHEMA_PATH = [
        "paths",
        "/objects/search",
        "post",
        "requestBody",
        "content",
        "application/json",
        "schema",
    ]
    type = serializers.URLField(
        required=True,
        allow_blank=False,
        help_text=_("OBJECTTYPE of OBJECT. Must be provided."),
    )

    def validate_type(self, ot: str) -> str:
        ots = fetch_objecttypes()
        if ot not in [ot["url"] for ot in ots]:
            raise serializers.ValidationError("OBJECTTYPE %s not found." % ot)

        meta_config = MetaObjectTypesConfig.get_solo()
        meta_config.meta_objecttype_urls
        if ot in list(MetaObjectTypesConfig.get_solo().meta_objecttype_urls.values()):
            raise serializers.ValidationError(
                "OBJECTTYPE %s is a `meta`-objecttype." % ot
            )
        return ot


class ZaakObjectProxySerializer(ProxySerializer):
    PROXY_SCHEMA_BASE = settings.EXTERNAL_API_SCHEMAS["ZRC_API_SCHEMA"]
    PROXY_SCHEMA_PATH = ["components", "schemas", "ZaakObject"]

    def validate(self, data):
        zaak = get_zaak(zaak_url=self.initial_data["zaak"])
        zaakobjecten = get_zaakobjecten(zaak)
        for zo in zaakobjecten:
            if all(
                [
                    self.initial_data["object"],
                    zo.object,
                    zo.object == self.initial_data["object"],
                ]
            ):
                raise serializers.ValidationError(
                    _("OBJECT is already related to ZAAK.")
                )
        object = fetch_object(self.initial_data["object"])
        if object["record"]["data"].get("afgestoten", False):
            raise serializers.ValidationError(
                _("`{ot}` is `afgestoten`.").format(ot=object["type"]["name"])
            )

        return self.initial_data

    def create(self, validated_data):
        if validated_data.get("object_type", "") == "overige":
            obj = fetch_object(self.initial_data["object"])
            if not validated_data.get("object_type_overige"):
                validated_data["object_type_overige"] = obj["type"]["name"]
            if not validated_data.get("object_type_overige_definitie"):
                latest_version = max(obj["type"]["versions"])
                validated_data["object_type_overige_definitie"] = {
                    "url": latest_version,
                    "schema": ".jsonSchema",
                    "objectData": ".record.data",
                }
            if not validated_data.get("relatieomschrijving"):
                validated_data["relatieomschrijving"] = (
                    f"{obj['type']['name']} van de ZAAK."
                )
        related_object = relate_object_to_zaak(validated_data)
        return related_object


class RecentlyViewedSerializer(serializers.Serializer):
    visited = serializers.DateTimeField(help_text=_("Datetime of last visit"))
    url = serializers.SerializerMethodField(
        help_text=_("URL of the ZAAK detail page in the zaakafhandelcomponent."),
    )
    identificatie = serializers.CharField(
        help_text=_("Unique identifier of ZAAK within `bronorganisatie`."),
    )
    omschrijving = serializers.SerializerMethodField(
        help_text=_("A short summary of the ZAAK.")
    )
    zaaktype_omschrijving = serializers.SerializerMethodField(
        help_text=_("Description of ZAAKTYPE.")
    )

    def get_omschrijving(self, obj) -> str:
        return find_zaak(
            bronorganisatie=obj["bronorganisatie"], identificatie=obj["identificatie"]
        ).omschrijving

    def get_zaaktype_omschrijving(self, obj) -> str:
        return find_zaak(
            bronorganisatie=obj["bronorganisatie"], identificatie=obj["identificatie"]
        ).zaaktype.omschrijving

    def get_url(self, obj: Dict) -> str:
        path = furl(settings.UI_ROOT_URL).path.segments + [
            "zaken",
            obj["bronorganisatie"],
            obj["identificatie"],
        ]
        return build_absolute_url(path, request=self.context["request"])


class ZaakHistorySerializer(serializers.ModelSerializer):
    zaak = serializers.URLField(
        required=True,
        help_text=_("URL-reference of the ZAAK"),
        allow_blank=False,
        write_only=True,
    )
    recently_viewed = RecentlyViewedSerializer(
        help_text=_("URL of the ZAAK detail page in the zaakafhandelcomponent."),
        read_only=True,
        many=True,
    )

    class Meta:
        model = User
        fields = ("zaak", "recently_viewed")

    def validate_zaak(self, zaak: str) -> Zaak:
        try:
            return get_zaak(zaak_url=zaak)
        except (ClientError, HTTPError) as exc:
            raise serializers.ValidationError(detail={"url": exc.args[0]})

    def validate(self, data) -> Dict:
        validated_data = super().validate(data)
        return {
            "visited": timezone.now().isoformat(),
            "bronorganisatie": validated_data["zaak"].bronorganisatie,
            "identificatie": validated_data["zaak"].identificatie,
        }

    def update(self, instance, validated_data):
        old_history = instance.recently_viewed
        old_history.append(validated_data)
        new_history = {}
        for old_entry in old_history:
            key = (old_entry["bronorganisatie"] + old_entry["identificatie"]).lower()
            if new_entry := new_history.get(key):
                new_history[key]["visited"] = max(
                    [old_entry["visited"], new_entry["visited"]]
                )
            else:
                new_history[key] = old_entry

        recently_viewed = sorted(
            list(new_history.values()),
            key=lambda dat: dat["visited"],
            reverse=True,
        )
        # only keep last 10 visited
        if len(recently_viewed) > 10:
            recently_viewed = recently_viewed[:10]

        return super().update(
            instance,
            {"recently_viewed": recently_viewed},
        )
