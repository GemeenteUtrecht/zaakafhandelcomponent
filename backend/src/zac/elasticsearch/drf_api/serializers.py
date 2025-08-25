import re
from typing import Dict

from django.conf import settings
from django.urls import reverse
from django.utils.timezone import is_naive, localtime, make_aware
from django.utils.translation import gettext_lazy as _

import pytz
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from zac.contrib.dowc.constants import DocFileTypes
from zac.contrib.dowc.fields import DowcUrlField
from zac.core.camunda.utils import resolve_assignee
from zac.core.fields import DownloadDocumentURLField

from ..documents import InformatieObjectDocument, ZaakDocument
from ..models import SearchReport
from .fields import OrderedMultipleChoiceField
from .utils import get_document_fields, get_document_properties

DEFAULT_ES_ZAAKDOCUMENT_FIELDS = [
    field[0]
    for field in get_document_fields(
        get_document_properties(ZaakDocument)["properties"]
    )
]

DEFAULT_ES_INFORMATIEOBJECTDOCUMENT_FIELDS = [
    field[0]
    for field in get_document_fields(
        get_document_properties(InformatieObjectDocument)["properties"]
    )
]


class ZaakIdentificatieSerializer(serializers.Serializer):
    identificatie = serializers.CharField(
        required=True,
        label=_("ZAAK identification"),
        help_text=_(
            "Enter a (part of the) ZAAK identification you wish to "
            "find, case insensitive."
        ),
    )


class SearchZaaktypeSerializer(serializers.Serializer):
    omschrijving = serializers.CharField(
        help_text=_(
            "Description of ZAAKTYPE, used as an aggregator of different versions of ZAAKTYPE."
        )
    )
    catalogus = serializers.URLField(help_text=_("URL-reference of related CATALOGUS."))


class SearchSerializer(serializers.Serializer):
    behandelaar = serializers.CharField(
        required=False, help_text=_("`username` of behandelaar.")
    )
    eigenschappen = serializers.JSONField(
        required=False,
        help_text=_(
            "ZAAK-EIGENSCHAPs in format `<property name>:{'value': <property value>}`."
        ),
    )
    fields = OrderedMultipleChoiceField(
        required=False,
        help_text=_(
            "Fields that will be returned with the search results. Default returns all fields. Will always include `identificatie` and `bronorganisatie`."
        ),
        choices=DEFAULT_ES_ZAAKDOCUMENT_FIELDS,
        default=DEFAULT_ES_ZAAKDOCUMENT_FIELDS,
    )
    identificatie = serializers.CharField(
        required=False,
        help_text=_("Unique identifier of ZAAK within `bronorganisatie`."),
    )
    include_closed = serializers.BooleanField(
        required=False,
        help_text=_("Include closed ZAAKen."),
        default=False,
    )
    object = serializers.URLField(
        required=False,
        help_text=_("URL-reference of OBJECT."),
    )
    omschrijving = serializers.CharField(
        required=False, help_text=_("Brief description of ZAAK.")
    )
    zaaktype = SearchZaaktypeSerializer(
        required=False, help_text=_("Properties to identify ZAAKTYPEs.")
    )

    def validate_omschrijving(self, omschrijving):
        return re.escape(omschrijving)

    def validate_fields(self, fields):
        if isinstance(fields, set):
            fields.add("identificatie")
            fields.add("bronorganisatie")
        return sorted(list(fields))

    def validate_eigenschappen(self, data):
        validated_data = dict()
        for name, value in data.items():
            if not isinstance(value, dict):
                raise serializers.ValidationError(
                    "'Eigenschappen' field values should be JSON objects"
                )
            if "value" not in value:
                raise serializers.ValidationError(
                    "'Eigenschappen' fields should include 'value' attribute"
                )
            validated_data[name] = re.escape(value["value"])
        return validated_data


class QuickSearchSerializer(serializers.Serializer):
    search = serializers.CharField(
        required=True,
        help_text=_(
            "A broad search that looks through ZAAKs, INFORMATIEOBJECTs and OBJECTs."
        ),
    )


class SearchReportSerializer(serializers.ModelSerializer):
    query = SearchSerializer()

    class Meta:
        model = SearchReport
        fields = (
            "id",
            "name",
            "query",
        )
        extra_kwargs = {
            "id": {"help_text": _("Id of search report.")},
            "name": {"help_text": _("Name of search report.")},
            "query": {"help_text": _("Query of search report.")},
        }


class EigenschapDocumentSerializer(serializers.Serializer):
    tekst = serializers.CharField(required=False)
    getal = serializers.DecimalField(required=False, max_digits=10, decimal_places=2)
    datum = serializers.DateField(required=False)
    datum_tijd = serializers.DateTimeField(required=False)


class BetrokkeneIdentificatieSerializer(serializers.Serializer):
    identificatie = serializers.CharField(
        required=False, help_text=_("Identification of the betrokkene.")
    )


class RolDocumentSerializer(serializers.Serializer):
    url = serializers.URLField(
        required=False, help_text=_("URL-reference of the ROL in Zaken API.")
    )
    betrokkene_type = serializers.CharField(help_text=_("`betrokkeneType` of the ROL."))
    omschrijving_generiek = serializers.CharField(
        help_text=_("Generic, brief description of the ROL.")
    )
    betrokkene_identificatie = BetrokkeneIdentificatieSerializer(
        required=False, help_text=_("A short unique identification of the betrokkene.")
    )


class ZaakTypeDocumentSerializer(serializers.Serializer):
    url = serializers.URLField(
        required=False,
        help_text=_("URL-reference of the ZAAKTYPE in the CATALOGI API."),
    )
    catalogus = serializers.CharField(
        required=False,
        help_text=_("URL-reference of the CATALOGUS that belongs to the ZAAKTYPE."),
    )
    catalogus_domein = serializers.CharField(
        required=False,
        help_text=_("`domein` the CATALOGUS that belongs to the ZAAKTYPE."),
    )
    omschrijving = serializers.CharField(
        required=False, help_text=_("Description of the ZAAKTYPE.")
    )
    identificatie = serializers.CharField(
        required=False,
        help_text=_(
            "Identificatie of ZAAKTYPE. Unique in related CATALOGUS of CATALOGI API."
        ),
    )


class StatusDocumentSerializer(serializers.Serializer):
    url = serializers.URLField(
        required=False, help_text=_("URL-reference of the STATUS in the ZAKEN API.")
    )
    statustype = serializers.CharField(
        required=False, help_text=_("STATUSTYPE description of the STATUS.")
    )
    datum_status_gezet = serializers.DateTimeField(
        required=False, help_text=_("Date at which the STATUS was given to the ZAAK.")
    )
    statustoelichting = serializers.CharField(
        required=False, help_text=_("Comment on the STATUS.")
    )


class ZaakObjectDocumentSerializer(serializers.Serializer):
    url = serializers.URLField(
        required=False, help_text=_("URL-reference of the ZAAKOBJECT in ZAKEN API.")
    )
    object = serializers.URLField(
        required=False, help_text=_("URL-reference of the OBJECT in OBJECTS API.")
    )


class ZaakInformatieObjectDocumentSerializer(serializers.Serializer):
    url = serializers.URLField(
        required=False,
        help_text=_("URL-reference of the ZAAKINFORMATIEOBJECT in ZAKEN API."),
    )
    informatieobject = serializers.URLField(
        required=False, help_text=_("URL-reference of the INFORMATIEOBJECT in DRC API.")
    )


class ZaakgeometrieSerializer(serializers.Serializer):
    type = serializers.CharField()
    coordinates = serializers.ListField()

    def to_representation(self, instance):
        if not instance:
            return None
        return super().to_representation(instance)


class ZaakDocumentSerializer(serializers.Serializer):
    url = serializers.URLField(
        required=False,
        help_text=_("URL-reference of the ZAAK in the ZAKEN API."),
    )
    zaaktype = ZaakTypeDocumentSerializer(
        required=False, help_text=_("ZAAKTYPE of the ZAAK.")
    )
    identificatie = serializers.CharField(
        required=False,
        help_text=_("Unique identifier of ZAAK within `bronorganisatie`."),
    )
    bronorganisatie = serializers.CharField(
        required=True,
        help_text=_("The RSIN of the organisation that created the ZAAK."),
    )
    omschrijving = serializers.CharField(
        required=False, help_text=_("Brief description of the ZAAK.")
    )
    vertrouwelijkheidaanduiding = serializers.CharField(
        required=False, help_text=_("Vertrouwelijkheidaanduiding of the ZAAK.")
    )
    va_order = serializers.IntegerField(
        required=False,
    )
    rollen = RolDocumentSerializer(
        required=False,
        many=True,
        help_text=_("ROLlen of the ZAAK that were involved at some point."),
    )
    startdatum = serializers.DateTimeField(
        required=False, help_text=_("Date at which the ZAAK processing starts.")
    )
    einddatum = serializers.DateTimeField(
        required=False, help_text=_("Date at which the ZAAK processing ends.")
    )
    registratiedatum = serializers.DateTimeField(
        required=False, help_text=_("Date at which the ZAAK was registered.")
    )
    deadline = serializers.DateTimeField(
        required=False,
        help_text=_(
            "Deadline of the ZAAK: returns `uiterlijke_einddatum_afdoening` if it's known. Otherwise it is calculated from `startdatum` and `doorlooptijd`."
        ),
    )
    eigenschappen = EigenschapDocumentSerializer(
        many=True, required=False, help_text=_("EIGENSCHAPs of the ZAAK.")
    )
    status = StatusDocumentSerializer(
        required=False, help_text=_("STATUS of the ZAAK.")
    )
    toelichting = serializers.CharField(
        required=False, help_text=_("Comment on the ZAAK.")
    )
    zaakobjecten = ZaakObjectDocumentSerializer(
        many=True, required=False, help_text=_("ZAAKOBJECTs belonging to the ZAAK.")
    )
    zaakgeometrie = ZaakgeometrieSerializer(
        required=False,
        help_text=_("A GeoJSON containing geometric information related to the ZAAK."),
    )
    zaakinformatieobjecten = ZaakInformatieObjectDocumentSerializer(
        many=True,
        required=False,
        help_text=_("ZAAKINFORMATIEOBJECTs belonging to the ZAAK."),
    )


class QSZaakDocumentSerializer(serializers.Serializer):
    identificatie = serializers.CharField(
        required=False,
        help_text=_("Unique identifier of ZAAK within `bronorganisatie`."),
    )
    bronorganisatie = serializers.CharField(
        required=True,
        help_text=_("The RSIN of the organisation that created the ZAAK."),
    )
    omschrijving = serializers.CharField(
        required=False, help_text=_("Brief description of the ZAAK.")
    )


class QSObjectDocumentSerializer(serializers.Serializer):
    related_zaken = QSZaakDocumentSerializer(
        many=True, help_text=_("ZAAKs that have a ZAAKOBJECT related to this OBJECT.")
    )
    record_data = serializers.SerializerMethodField(
        help_text=_("Record data of OBJECT.")
    )
    string_representation = serializers.CharField(
        required=True,
        allow_blank=True,
        help_text=_("A user-friendly string representation of the OBJECT."),
    )

    def get_record_data(self, obj) -> Dict:
        return obj.to_dict().get("record_data", {})


class QSInformatieObjectDocumentSerializer(serializers.Serializer):
    titel = serializers.CharField(
        required=True,
        help_text=_("Title of the INFORMATIEOBJECT. Includes the file extension."),
    )
    related_zaken = QSZaakDocumentSerializer(
        many=True,
        help_text=_(
            "ZAAKs that have a ZAAKINFORMATIEOBJECT related to this INFORMATIEOBJECT."
        ),
    )


class QuickSearchResultSerializer(serializers.Serializer):
    zaken = QSZaakDocumentSerializer(
        many=True, help_text=_("ZAAKs related to quick search query.")
    )
    documenten = QSInformatieObjectDocumentSerializer(
        many=True, help_text=_("INFORMATIEOBJECTs related to quick search query.")
    )
    objecten = QSObjectDocumentSerializer(
        many=True, help_text=_("OBJECTs related to quick search query.")
    )


class SearchInformatieObjectSerializer(serializers.Serializer):
    fields = OrderedMultipleChoiceField(
        required=False,
        help_text=_(
            "Fields that will be returned with the search results. Default returns all fields."
        ),
        choices=DEFAULT_ES_INFORMATIEOBJECTDOCUMENT_FIELDS
        + [
            "delete_url",
            "read_url",
            "write_url",
            "current_user_is_editing",
            "last_edited_date",
        ],
        default=[
            "auteur",
            "beschrijving",
            "bestandsnaam",
            "bestandsomvang",
            "bronorganisatie",
            "current_user_is_editing",
            "delete_url",
            "identificatie",
            "informatieobjecttype",
            "last_edited_date",
            "locked",
            "read_url",
            "titel",
            "url",
            "versie",
            "vertrouwelijkheidaanduiding",
            "write_url",
        ],
    )


class ESInformatieObjectTypeSerializer(serializers.Serializer):
    url = serializers.URLField(help_text=_("URL-reference to INFORMATIEOBJECTTYPE."))
    omschrijving = serializers.CharField(help_text=_("Description."))


class ESListZaakDocumentSerializer(serializers.Serializer):
    auteur = serializers.CharField(help_text=_("Author to last edit."))
    beschrijving = serializers.CharField(help_text=_("Description."))
    bestandsnaam = serializers.CharField(help_text=_("Filename."))
    bestandsomvang = serializers.IntegerField(help_text=_("File size in bytes."))
    bronorganisatie = serializers.CharField(
        help_text=_("The RSIN of the organisation that created the INFORMATIEOBJECT."),
    )
    current_user_is_editing = serializers.SerializerMethodField(
        help_text=_(
            "Boolean flag to indicate if requesting user is editing current INFORMATIEOBJECT."
        )
    )
    delete_url = serializers.SerializerMethodField(
        help_text=_(
            "The URL required to save edits and delete the DOWC object related to the INFORMATIEOBJECT."
        )
    )
    download_url = DownloadDocumentURLField()
    identificatie = serializers.CharField()
    informatieobjecttype = ESInformatieObjectTypeSerializer(
        help_text=_("The INFORMATIEOBJECTTYPE related to the ZAAKINFORMATIEOBJECT.")
    )
    last_edited_date = serializers.DateTimeField(
        help_text=_("Shows last edited datetime."), allow_null=True
    )
    locked = serializers.BooleanField()
    locked_by = serializers.SerializerMethodField(
        help_text=_("Email of user that locked document.")
    )
    read_url = DowcUrlField(
        purpose=DocFileTypes.read,
        help_text=_(
            "URL to read INFORMATIEOBJECT. Opens the appropriate Microsoft Office application."
        ),
    )
    related_zaken = QSZaakDocumentSerializer(many=True)
    titel = serializers.CharField(help_text=_("Title given to INFORMATIEOBJECT."))
    url = serializers.URLField(help_text=_("URL-reference to INFORMATIEOBJECT."))
    versie = serializers.IntegerField(help_text=_("Version."))
    vertrouwelijkheidaanduiding = serializers.CharField(
        help_text=_("Vertrouwelijkheidaanduiding of INFORMATIEOBJECT."),
    )
    write_url = DowcUrlField(
        purpose=DocFileTypes.write,
        allow_blank=True,
        help_text=_(
            "URL to write INFORMATIEOBJECT. Opens the appropriate Microsoft Office application."
        ),
    )

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


class VGUReportInputSerializer(serializers.Serializer):
    start_period = serializers.DateTimeField(
        required=True,
        help_text=_("Start date of the period for which the report is generated."),
    )
    end_period = serializers.DateTimeField(
        required=True,
        help_text=_("End date of the period for which the report is generated."),
    )

    def validate(self, attrs):
        data = super().validate(attrs)
        # If start_period wasn't provided, use today's date
        start_period = data.get("start_period") or date.today()
        end_period = data.get("end_period")

        if end_period and end_period <= start_period:
            raise serializers.ValidationError(
                _("Start date needs to be earlier than end date.")
            )
        return data


class VGUReportZakenSerializer(serializers.Serializer):
    identificatie = serializers.CharField(
        help_text=_("Unique identifier of the ZAAK within `bronorganisatie`."),
    )
    omschrijving = serializers.CharField(help_text=_("`omschrijving` of the ZAAK."))
    zaaktype = serializers.CharField(
        help_text=_("`omschrijving` of the ZAAKTYPE."),
        source="zaaktype_omschrijving",
    )
    registratiedatum = serializers.SerializerMethodField(
        help_text=_("Date at which the ZAAK was registered."),
    )
    initiator = serializers.SerializerMethodField(
        help_text=_("The initiator of the ZAAK, if available.")
    )
    objecten = serializers.CharField(
        help_text=_(
            "A comma-separated list of OBJECTs related to ZAAK. If no OBJECTs are related, this field will be empty."
        ),
    )
    aantal_informatieobjecten = serializers.IntegerField(
        help_text=_("The number of INFORMATIEOBJECTs related to the ZAAK."),
        source="zios_count",
    )

    def get_initiator(self, obj) -> str:
        """
        Returns the initiator of the ZAAK if available.
        """
        if obj.get("initiator_rol", None):
            obj["initiator"] = resolve_assignee(obj["initiator_rol"])
        return str(obj["initiator"].email) if obj["initiator"] else ""

    @extend_schema_field(serializers.DateField())
    def get_registratiedatum(self, obj) -> str:
        dt = obj.get("registratiedatum")
        if dt:
            if is_naive(dt):
                dt = make_aware(dt, timezone=pytz.timezone(settings.TIME_ZONE))
            return localtime(dt).date().isoformat()
        return ""


class VGUReportIOSerializer(serializers.Serializer):
    """
    Serializer for usage_report_informatieobjecten() results.

    Expected input per item:
      {
        "auteur": str,
        "bestandsnaam": str,
        "informatieobjecttype": str,
        "creatiedatum": datetime|None,
        "gerelateerde_zaken": List[str],  # e.g. ["ABC123: Zaken algemeen", ...]
      }
    """

    auteur = serializers.CharField(allow_blank=True, required=False)
    bestandsnaam = serializers.CharField(allow_blank=True, required=False)
    informatieobjecttype = serializers.CharField(allow_blank=True, required=False)
    creatiedatum = serializers.DateTimeField(allow_null=True, required=False)
    gerelateerde_zaken = serializers.ListField(
        child=serializers.CharField(allow_blank=True),
        required=False,
    )
