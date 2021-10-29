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
    object = serializers.URLField(
        required=False,
        help_text=_("URL of OBJECT"),
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
    datum = serializers.DateField(required=False)
    datum_tijd = serializers.DateTimeField(required=False)


class BetrokkeneIdentificatieSerializer(serializers.Serializer):
    identificatie = serializers.CharField(
        required=False, help_text=_("Identification of the betrokkene.")
    )


class RolDocumentSerializer(serializers.Serializer):
    url = serializers.URLField(
        required=False, help_text=_("URL reference of the ROL in Zaken API.")
    )
    betrokkene_type = serializers.CharField(help_text=_("Betrokkene type of the ROL."))
    omschrijving_generiek = serializers.CharField(
        help_text=_("Generic, brief description of the ROL.")
    )
    betrokkene_identificatie = BetrokkeneIdentificatieSerializer(
        required=False, help_text=_("A short unique identification of the betrokkene.")
    )


class ZaakTypeDocumentSerializer(serializers.Serializer):
    url = serializers.URLField(
        required=False,
        help_text=_("URL reference of the ZAAKTYPE in the Catalogi API."),
    )
    catalogus = serializers.CharField(
        required=False,
        help_text=_("URL reference of the CATALOGUS that belongs to the ZAAKTYPE."),
    )
    omschrijving = serializers.CharField(
        required=False, help_text=_("Description of the ZAAKTYPE.")
    )


class StatusDocumentSerializer(serializers.Serializer):
    url = serializers.URLField(
        required=False, help_text=_("URL reference of the STATUS in Zaken API.")
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
        required=False, help_text=_("URL reference of the ZAAKOBJECT in Zaken API.")
    )
    object = serializers.URLField(
        required=False, help_text=_("URL reference of the OBJECT in Objects API.")
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
        help_text=_("URL reference of the ZAAK in Zaken API."),
    )
    zaaktype = ZaakTypeDocumentSerializer(
        required=False, help_text=_("ZAAKTYPE of the ZAAK.")
    )
    identificatie = serializers.CharField(
        required=False, help_text=_("Unique identification of the ZAAK.")
    )
    bronorganisatie = serializers.CharField(
        required=True,
        help_text=_("The RSIN of the organisation that created the the ZAAK."),
    )
    omschrijving = serializers.CharField(
        required=False, help_text=_("Brief description of the ZAAK.")
    )
    vertrouwelijkheidaanduiding = serializers.CharField(
        required=False, help_text=_("Confidentiality classification of the ZAAK.")
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
            "Deadline of the ZAAK: returns 'uiterlijke_einddatum_afdoening' if it known. Otherwise it is calculated from 'startdatum' and 'doorlooptijd'."
        ),
    )
    eigenschappen = EigenschapDocumentSerializer(
        many=True, required=False, help_text=_("EIGENSCHAPpen of the ZAAK.")
    )
    status = StatusDocumentSerializer(
        required=False, help_text=_("STATUS of the ZAAK.")
    )
    toelichting = serializers.CharField(
        required=False, help_text=_("Comment on the ZAAK.")
    )
    zaakobjecten = ZaakObjectDocumentSerializer(
        many=True, required=False, help_text=_("ZAAKOBJECTen belonging to the ZAAK.")
    )
    zaakgeometrie = ZaakgeometrieSerializer(
        required=False,
        help_text=_("A GeoJSON containing geometric information related to the ZAAK."),
    )
