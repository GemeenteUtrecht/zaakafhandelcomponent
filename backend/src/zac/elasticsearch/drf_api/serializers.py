import re
from typing import Dict

from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from ..documents import ZaakDocument
from ..models import SearchReport
from .fields import OrderedMultipleChoiceField
from .utils import get_document_fields, get_document_properties

DEFAULT_ES_ZAAKDOCUMENT_FIELDS = [
    field[0]
    for field in get_document_fields(
        get_document_properties(ZaakDocument)["properties"]
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
    identificatie = serializers.CharField(
        required=False,
        help_text=_("Unique identifier of ZAAK within `bronorganisatie`."),
    )
    zaaktype = SearchZaaktypeSerializer(
        required=False, help_text=_("Properties to identify ZAAKTYPEs.")
    )
    omschrijving = serializers.CharField(
        required=False, help_text=_("Brief description of ZAAK.")
    )
    eigenschappen = serializers.JSONField(
        required=False,
        help_text=_(
            "ZAAK-EIGENSCHAPs in format `<property name>:{'value': <property value>}`."
        ),
    )
    object = serializers.URLField(
        required=False,
        help_text=_("URL-reference of OBJECT."),
    )
    fields = OrderedMultipleChoiceField(
        required=False,
        help_text=_(
            "Fields that will be returned with the search results. Default returns all fields. Will always include `identificatie` and `bronorganisatie`."
        ),
        choices=DEFAULT_ES_ZAAKDOCUMENT_FIELDS,
        default=DEFAULT_ES_ZAAKDOCUMENT_FIELDS,
    )
    include_closed = serializers.BooleanField(
        required=False,
        help_text=_("Include closed ZAAKen."),
        default=False,
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
        required=False, help_text=_("Unique identification of the ZAAK.")
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
        required=False, help_text=_("Unique identification of the ZAAK.")
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
