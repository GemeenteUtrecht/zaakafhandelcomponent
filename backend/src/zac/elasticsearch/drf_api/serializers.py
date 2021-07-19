from django.utils.translation import gettext_lazy as _

from rest_framework import serializers

from ..documents import ZaakDocument
from ..models import SearchReport
from .fields import OrderedMultipleChoiceField
from .utils import get_document_fields, get_document_properties

DEFAULT_ES_FIELDS = [
    field[0]
    for field in get_document_fields(
        get_document_properties(ZaakDocument)["properties"]
    )
]


class ZaakIdentificatieSerializer(serializers.Serializer):
    identificatie = serializers.CharField(
        required=True,
        label=_("zaak identification"),
        help_text=_(
            "Enter a (part) of the zaak identification you wish to "
            "find, case insensitive."
        ),
    )


class SearchZaaktypeSerializer(serializers.Serializer):
    omschrijving = serializers.CharField(
        help_text=_(
            "Description of ZAAKTYPE, used as an aggregator of different versions of ZAAKTYPE"
        )
    )
    catalogus = serializers.URLField(help_text=_("Url reference of related CATALOGUS"))


class SearchSerializer(serializers.Serializer):
    identificatie = serializers.CharField(
        required=False,
        help_text=_("Unique identifier of ZAAK within `bronorganisatie`"),
    )
    zaaktype = SearchZaaktypeSerializer(
        required=False, help_text=_("Properties to identify ZAAKTYPEn")
    )
    omschrijving = serializers.CharField(
        required=False, help_text=_("Brief description of ZAAK")
    )
    eigenschappen = serializers.JSONField(
        required=False,
        help_text=_(
            "ZAAK-EIGENSCHAPpen in format `<property name>:{'value': <property value>}`"
        ),
    )
    fields = OrderedMultipleChoiceField(
        required=False,
        help_text=_(
            "Fields that will be returned with the search results. Default returns all fields. Will always include <identificatie>."
        ),
        choices=DEFAULT_ES_FIELDS,
        default=DEFAULT_ES_FIELDS,
    )
    include_closed = serializers.BooleanField(
        required=False,
        help_text=_("Include closed ZAKEN."),
        default=False,
    )

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
            validated_data[name] = value["value"]
        return validated_data


class SearchReportSerializer(serializers.ModelSerializer):
    query = SearchSerializer()

    class Meta:
        model = SearchReport
        fields = (
            "id",
            "name",
            "query",
        )


class EigenschapDocumentSerializer(serializers.Serializer):
    tekst = serializers.CharField(required=False)
    getal = serializers.DecimalField(required=False, max_digits=10, decimal_places=2)
    datum = serializers.DateField(format="%d-%m-%Y", required=False)
    datum_tijd = serializers.DateTimeField(format="%d-%m-%Y %H:%M:%S", required=False)


class BetrokkeneIdentificatieSerializer(serializers.Serializer):
    identificatie = serializers.CharField(required=False)


class RolDocumentSerializer(serializers.Serializer):
    url = serializers.URLField(required=False)
    betrokkene_type = serializers.CharField()
    omschrijving_generiek = serializers.CharField()
    betrokkene_identificatie = BetrokkeneIdentificatieSerializer(required=False)


class ZaakTypeDocumentSerializer(serializers.Serializer):
    url = serializers.URLField(required=False)
    catalogus = serializers.CharField(required=False)
    omschrijving = serializers.CharField(required=False)


class ZaakDocumentSerializer(serializers.Serializer):
    url = serializers.URLField(required=False)
    zaaktype = ZaakTypeDocumentSerializer(required=False)
    identificatie = serializers.CharField(required=False)
    bronorganisatie = serializers.CharField(required=True)
    omschrijving = serializers.CharField(required=False)
    vertrouwelijkheidaanduiding = serializers.CharField(required=False)
    va_order = serializers.IntegerField(required=False)
    rollen = RolDocumentSerializer(required=False, many=True)
    startdatum = serializers.DateTimeField(format="%d-%m-%YT%H:%M:%S", required=False)
    einddatum = serializers.DateTimeField(format="%d-%m-%YT%H:%M:%S", required=False)
    registratiedatum = serializers.DateTimeField(
        format="%d-%m-%YT%H:%M:%S", required=False
    )
    deadline = serializers.DateTimeField(format="%d-%m-%YT%H:%M:%S", required=False)
    eigenschappen = EigenschapDocumentSerializer(many=True, required=False)
