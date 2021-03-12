from django.core.validators import RegexValidator
from django.template.defaultfilters import filesizeformat
from django.urls import reverse
from django.utils.translation import gettext as _

from rest_framework import serializers
from zgw_consumers.api_models.catalogi import (
    EIGENSCHAP_FORMATEN,
    Eigenschap,
    EigenschapSpecificatie,
    InformatieObjectType,
    ResultaatType,
    StatusType,
    ZaakType,
)
from zgw_consumers.api_models.constants import (
    AardRelatieChoices,
    RolTypes,
    VertrouwelijkheidsAanduidingen,
)
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.api_models.zaken import Resultaat, Status, ZaakEigenschap
from zgw_consumers.drf.serializers import APIModelSerializer

from zac.api.polymorphism import PolymorphicSerializer
from zac.contrib.dowc.constants import DocFileTypes
from zac.contrib.dowc.utils import get_dowc_url
from zac.core.rollen import Rol
from zgw.models.zrc import Zaak

from ..zaakobjecten import ZaakObjectGroup
from .utils import (
    CSMultipleChoiceField,
    TypeChoices,
    ValidExpandChoices,
    ValidFieldChoices,
    get_informatieobjecttypen_for_zaak,
)


class InformatieObjectTypeSerializer(serializers.Serializer):
    url = serializers.URLField()
    omschrijving = serializers.CharField()


class AddDocumentSerializer(serializers.Serializer):
    informatieobjecttype = serializers.URLField(required=True)
    zaak = serializers.URLField(required=True)
    file = serializers.FileField(required=True, use_url=False)

    beschrijving = serializers.CharField(required=False)

    def validate(self, data):
        zaak_url = data.get("zaak")
        informatieobjecttype_url = data.get("informatieobjecttype")

        if zaak_url and informatieobjecttype_url:
            informatieobjecttypen = get_informatieobjecttypen_for_zaak(zaak_url)
            present = any(
                iot
                for iot in informatieobjecttypen
                if iot.url == informatieobjecttype_url
            )
            if not present:
                raise serializers.ValidationError(
                    "Invalid informatieobjecttype URL given."
                )

        return data


class AddDocumentResponseSerializer(serializers.Serializer):
    document = serializers.URLField(source="url")


class DocumentInfoSerializer(serializers.Serializer):
    document_type = serializers.CharField(source="informatieobjecttype.omschrijving")
    titel = serializers.CharField()
    vertrouwelijkheidaanduiding = serializers.CharField(
        source="get_vertrouwelijkheidaanduiding_display"
    )
    bestandsgrootte = serializers.SerializerMethodField()

    read_url = serializers.SerializerMethodField(
        label=_("ZAC document read URL"),
        help_text=_(
            "The document URL for the end user that opens a document to be read. Will "
            "serve the file from a WebDAV server."
        ),
    )

    def get_bestandsgrootte(self, obj):
        return filesizeformat(obj.bestandsomvang)

    def get_read_url(self, obj) -> str:
        return get_dowc_url(obj, purpose=DocFileTypes.read)


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
    relation_zaak = serializers.URLField(required=True)
    aard_relatie = serializers.ChoiceField(required=True, choices=AardRelatieChoices)
    main_zaak = serializers.URLField(required=True)

    def validate(self, data):
        """Check that the main zaak and the relation are not the same"""

        if data["relation_zaak"] == data["main_zaak"]:
            raise serializers.ValidationError(
                _("Zaken kunnen niet met zichzelf gerelateerd worden.")
            )
        return data


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


class ZaakDetailSerializer(APIModelSerializer):
    zaaktype = ZaakTypeSerializer()
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
            "uiterlijke_einddatum_afdoening",
            "vertrouwelijkheidaanduiding",
            "deadline",
            "deadline_progress",
            "resultaat",
        )


class UpdateZaakDetailSerializer(APIModelSerializer):
    reden = serializers.CharField(
        help_text=_("Reason for the edit, used in audit trail."),
    )
    vertrouwelijkheidaanduiding = serializers.ChoiceField(
        VertrouwelijkheidsAanduidingen.choices,
        help_text=_("The confidentiality level of the case."),
    )

    class Meta:
        model = Zaak
        fields = (
            "einddatum",
            "einddatum_gepland",
            "omschrijving",
            "reden",
            "toelichting",
            "uiterlijke_einddatum_afdoening",
            "vertrouwelijkheidaanduiding",
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
            },
            "toelichting": {
                "required": False,
            },
            "uiterlijke_einddatum_afdoening": {
                "required": False,
            },
            "vertrouwelijkheidaanduiding": {
                "required": False,
            },
        }


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
    specificatie = EigenschapSpecificatieSerializer(label=_("property definition"))

    class Meta:
        model = Eigenschap
        fields = (
            "url",
            "naam",
            "toelichting",
            "specificatie",
        )


class CharValueSerializer(APIModelSerializer):
    value = serializers.CharField(
        label=_("property value"),
        source="get_waarde",
    )

    class Meta:
        model = ZaakEigenschap
        fields = ("value",)


class NumberValueSerializer(APIModelSerializer):
    value = serializers.DecimalField(
        label=_("property value"),
        source="get_waarde",
        max_digits=100,
        decimal_places=20,
    )

    class Meta:
        model = ZaakEigenschap
        fields = ("value",)


class DateValueSerializer(APIModelSerializer):
    value = serializers.DateField(
        label=_("property value"),
        source="get_waarde",
    )

    class Meta:
        model = ZaakEigenschap
        fields = ("value",)


class DateTimeValueSerializer(APIModelSerializer):
    value = serializers.DateTimeField(
        label=_("property value"),
        source="get_waarde",
    )

    class Meta:
        model = ZaakEigenschap
        fields = ("value",)


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
    eigenschap = EigenschapSerializer()

    class Meta:
        model = ZaakEigenschap
        fields = (
            "url",
            "formaat",
            "eigenschap",
        )


class DocumentTypeSerializer(APIModelSerializer):
    class Meta:
        model = InformatieObjectType
        fields = (
            "url",
            "omschrijving",
        )


class ZaakDocumentSerializer(APIModelSerializer):
    read_url = serializers.SerializerMethodField(
        label=_("ZAC document read URL"),
        help_text=_(
            "The document URL for the end user that opens a document to be read. Will serve the file from a WebDAV server."
        ),
    )
    write_url = serializers.SerializerMethodField(
        label=_("ZAC document write URL"),
        help_text=_(
            "The document URL for the end user that opens a document to be written. Will serve the file from a WebDAV server."
        ),
    )
    vertrouwelijkheidaanduiding = serializers.CharField(
        source="get_vertrouwelijkheidaanduiding_display"
    )
    informatieobjecttype = DocumentTypeSerializer()

    class Meta:
        model = Document
        fields = (
            "url",
            "auteur",
            "identificatie",
            "beschrijving",
            "bestandsnaam",
            "locked",
            "informatieobjecttype",
            "titel",
            "vertrouwelijkheidaanduiding",
            "bestandsomvang",
            "read_url",
            "write_url",
        )
        extra_kwargs = {
            "bestandsomvang": {
                "help_text": _("File size in bytes"),
            }
        }

    def get_read_url(self, obj) -> str:
        return get_dowc_url(obj, purpose=DocFileTypes.read)

    def get_write_url(self, obj) -> str:
        return get_dowc_url(obj, purpose=DocFileTypes.write)


class RelatedZaakDetailSerializer(ZaakDetailSerializer):
    status = ZaakStatusSerializer()

    class Meta(ZaakDetailSerializer.Meta):
        fields = ZaakDetailSerializer.Meta.fields + ("status",)


class RelatedZaakSerializer(serializers.Serializer):
    aard_relatie = serializers.CharField()
    zaak = RelatedZaakDetailSerializer()


class RolSerializer(APIModelSerializer):
    name = serializers.CharField(source="get_name")
    identificatie = serializers.CharField(source="get_identificatie")
    betrokkene_type = serializers.ChoiceField(choices=RolTypes)
    betrokkene_type_display = serializers.CharField(
        source="get_betrokkene_type_display"
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
        )


class ZaakObjectGroupSerializer(APIModelSerializer):
    items = serializers.ListField(
        child=serializers.JSONField(),
        help_text=_(
            "Collection of object-type specific items. "
            "The schema is determined by the usptream API(s). "
            "See `zac.core.zaakobjecten` for the available implementations."
        ),
    )

    class Meta:
        model = ZaakObjectGroup
        fields = ("object_type", "label", "items")


class ZaakTypeAggregateSerializer(serializers.Serializer):
    omschrijving = serializers.CharField(
        help_text=_(
            "Description of ZAAKTYPE, used as an aggregator of different versions of ZAAKTYPE"
        )
    )
    identificatie = serializers.CharField(
        help_text=_(
            "Identifier of ZAAKTYPE, different ZAAKTYPE versions can share the same identifier"
        )
    )
    catalogus = serializers.URLField(help_text=_("Url reference of related CATALOGUS"))


class SearchEigenschapSpecificatieSerializer(serializers.Serializer):
    type = serializers.ChoiceField(
        choices=TypeChoices.choices,
        help_text=_("According to JSON schema date values have `string` type"),
    )
    format = serializers.CharField(
        required=False,
        help_text=_(
            "Used to differentiate `date` and `date-time` values from other strings"
        ),
    )
    min_length = serializers.IntegerField(
        required=False, help_text=_("Only for strings")
    )
    max_length = serializers.IntegerField(
        required=False, help_text=_("Only for strings")
    )
    enum = serializers.ListField(
        required=False, help_text=_("An array of possible values")
    )

    def get_enum_child_field(self, instance):
        enum = instance.get("enum")

        if not enum:
            return serializers.CharField()

        if instance["type"] == "string":
            return serializers.CharField()

        for el in enum:
            if not isinstance(el, int):
                return serializers.FloatField()

        return serializers.IntegerField()

    def to_representation(self, instance):
        self.fields["enum"].child = self.get_enum_child_field(instance)

        result = super().to_representation(instance)

        return result


class SearchEigenschapSerializer(serializers.Serializer):
    name = serializers.CharField(help_text=_("Name of EIGENSCHAP"))
    spec = SearchEigenschapSpecificatieSerializer(
        label=_("property definition"),
        help_text=_("JSON schema-ish specification of related ZAAK-EIGENSCHAP values"),
    )
