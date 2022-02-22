import pathlib
from decimal import ROUND_05UP
from typing import Optional

from django.conf import settings
from django.core.validators import RegexValidator
from django.template.defaultfilters import filesizeformat
from django.utils.translation import gettext as _

from furl import furl
from requests.exceptions import HTTPError
from rest_framework import serializers
from zds_client.client import ClientError
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

from zac.accounts.api.serializers import AtomicPermissionSerializer
from zac.accounts.models import User
from zac.api.polymorphism import PolymorphicSerializer
from zac.api.proxy import ProxySerializer
from zac.contrib.dowc.constants import DocFileTypes
from zac.contrib.dowc.fields import DowcUrlFieldReadOnly
from zac.core.rollen import Rol
from zac.core.services import (
    fetch_zaaktype,
    get_document,
    get_documenten,
    get_informatieobjecttypen_for_zaak,
    get_statustypen,
    get_zaak,
)
from zgw.models.zrc import Zaak

from ..zaakobjecten import ZaakObjectGroup
from .data import VertrouwelijkheidsAanduidingData
from .fields import NullableJsonField
from .utils import (
    CSMultipleChoiceField,
    TypeChoices,
    ValidExpandChoices,
    ValidFieldChoices,
)


class InformatieObjectTypeSerializer(APIModelSerializer):
    class Meta:
        model = InformatieObjectType
        fields = (
            "url",
            "omschrijving",
        )


class GetZaakDocumentSerializer(APIModelSerializer):
    read_url = DowcUrlFieldReadOnly(purpose=DocFileTypes.read)
    write_url = DowcUrlFieldReadOnly(purpose=DocFileTypes.write)
    vertrouwelijkheidaanduiding = serializers.CharField(
        source="get_vertrouwelijkheidaanduiding_display"
    )
    informatieobjecttype = InformatieObjectTypeSerializer()
    current_user_is_editing = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = (
            "auteur",
            "beschrijving",
            "bestandsnaam",
            "bestandsomvang",
            "current_user_is_editing",
            "identificatie",
            "informatieobjecttype",
            "locked",
            "read_url",
            "titel",
            "url",
            "versie",
            "vertrouwelijkheidaanduiding",
            "write_url",
        )
        extra_kwargs = {
            "bestandsomvang": {
                "help_text": _("File size in bytes"),
            }
        }

    def get_current_user_is_editing(self, obj) -> Optional[bool]:
        versioned_url = furl(obj.url)
        versioned_url.args["versie"] = obj.versie
        if "open_documenten" in self.context:
            if versioned_url.url in self.context["open_documenten"]:
                return True
            else:
                return False
        return None


class AddZaakDocumentSerializer(serializers.Serializer):
    beschrijving = serializers.CharField(
        required=False, help_text=_("Description of the document")
    )
    file = serializers.FileField(
        required=False,
        use_url=False,
        help_text=_("Content of the document. Mutually exclusive with `url` attribute"),
    )
    informatieobjecttype = serializers.URLField(
        required=False,
        help_text=_(
            "URL of informatiobjecttype in Catalogi API. Required if `file` is provided"
        ),
    )
    url = serializers.URLField(
        required=False,
        help_text=_(
            "URL of document in Documenten API. Mutually exclusive with `file` attribute"
        ),
    )
    zaak = serializers.URLField(
        required=True,
        help_text=_("URL of the zaak in Zaken API"),
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

            informatieobjecttype_url = document.informatieobjecttype

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
    file = serializers.FileField(required=False, use_url=False)
    reden = serializers.CharField(
        help_text=_("Reason for the edit, used in audit trail."),
        required=True,
        allow_null=True,
    )
    url = serializers.URLField(help_text=_("URL of document"), allow_blank=False)
    vertrouwelijkheidaanduiding = serializers.ChoiceField(
        choices=VertrouwelijkheidsAanduidingen.choices,
        help_text=_("Confidentiality classification."),
        required=False,
    )
    zaak = serializers.URLField(
        required=True,
        help_text=_("URL of the case."),
        allow_blank=False,
    )
    bestandsnaam = serializers.CharField(
        help_text=_("Filename without extension."),
        required=False,
    )

    def validate(self, data):
        document_url = data.get("url")
        zaak = get_zaak(zaak_url=data["zaak"])
        documenten, gone = get_documenten(zaak)
        documenten = {document.url: document for document in documenten}

        if document := documenten.get(document_url):
            if new_fn := data.get("bestandsnaam"):
                suffixes = pathlib.Path(document.bestandsnaam).suffixes
                data["bestandsnaam"] = new_fn + "".join(suffixes)
                data["titel"] = data["bestandsnaam"]
        else:
            raise serializers.ValidationError(
                _("The document is unrelated to ZAAK %s." % zaak.url)
            )

        return data


class DocumentInfoSerializer(serializers.Serializer):
    document_type = serializers.CharField(source="informatieobjecttype.omschrijving")
    titel = serializers.CharField()
    vertrouwelijkheidaanduiding = serializers.CharField(
        source="get_vertrouwelijkheidaanduiding_display"
    )
    bestandsgrootte = serializers.SerializerMethodField()

    read_url = DowcUrlFieldReadOnly(purpose=DocFileTypes.read)

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
    relation_zaak = serializers.URLField(
        required=True, help_text=_("The ZAAK that is to be related to the main ZAAK.")
    )
    aard_relatie = serializers.ChoiceField(
        required=True,
        choices=AardRelatieChoices,
        help_text=_(
            "The nature of the relationship between the main ZAAK and the related ZAAK."
        ),
    )
    main_zaak = serializers.URLField(
        required=True, help_text=_("The URL-reference to the main ZAAK.")
    )
    aard_relatie_omgekeerde_richting = serializers.ChoiceField(
        required=True,
        choices=AardRelatieChoices,
        help_text=_("The nature of the reverse relationship."),
    )

    def validate(self, data):
        """Check that the main zaak and the relation are not the same nor have the same relationship."""

        if data["relation_zaak"] == data["main_zaak"]:
            raise serializers.ValidationError(
                _("Zaken kunnen niet met zichzelf gerelateerd worden.")
            )

        if data["aard_relatie"] == data["aard_relatie_omgekeerde_richting"]:
            raise serializers.ValidationError(
                _("De aard van de zaak relaties kunnen niet hetzelfde zijn.")
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
    zaakgeometrie = serializers.JSONField(
        required=False,
        help_text=_("GeoJSON which represents the coordinates of the zaak"),
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
            "uiterlijke_einddatum_afdoening",
            "vertrouwelijkheidaanduiding",
            "zaakgeometrie",
            "deadline",
            "deadline_progress",
            "resultaat",
        )


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
        help_text=_("The confidentiality level of the case."),
    )
    zaakgeometrie = NullableJsonField(
        required=False,
        allow_null=True,
        help_text=_("GeoJSON which represents the coordinates of the zaak"),
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
            "uiterlijke_einddatum_afdoening": {
                "required": False,
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
            raise serializers.ValidationError("Invalid statustype URL given.")
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
    # TODO: Ideally this should be dynamic based on eigenschapsspecificatie
    value = serializers.DecimalField(
        label=_("property value"),
        source="get_waarde",
        max_digits=100,
        decimal_places=2,
        rounding=ROUND_05UP,
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
    eigenschap = EigenschapSerializer(read_only=True)

    class Meta:
        model = ZaakEigenschap
        fields = (
            "url",
            "formaat",
            "eigenschap",
        )
        extra_kwargs = {"url": {"read_only": True}}


class CreateZaakEigenschapSerializer(serializers.Serializer):
    naam = serializers.CharField(
        help_text=_(
            "Name of EIGENSCHAP. Must match EIGENSCHAP name as defined in Catalogi API."
        )
    )
    value = serializers.CharField(
        help_text=_(
            "Value of ZAAKEIGENSCHAP. Must be able to be formatted as defined by the EIGENSCHAP spec."
        )
    )
    zaak_url = serializers.URLField(help_text=_("URL-reference to ZAAK."))


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


class MedewerkerIdentificatieSerializer(serializers.Serializer):
    voorletters = serializers.SerializerMethodField()
    achternaam = serializers.SerializerMethodField()
    identificatie = serializers.CharField()
    voorvoegsel_achternaam = serializers.CharField()

    def get_voorletters(self, attrs):
        user = self.context.get("user")
        if user:
            voorletters = "".join(
                [part[0].upper() + "." for part in user.first_name.split()]
            ).strip()
            return voorletters or attrs["voorletters"]
        return attrs["voorletters"]

    def get_achternaam(self, attrs):
        user = self.context.get("user")
        if user:
            return user.last_name.capitalize() or attrs["achternaam"]
        return attrs["achternaam"]


class UpdateRolSerializer(APIModelSerializer):
    betrokkene_identificatie = MedewerkerIdentificatieSerializer()

    class Meta:
        model = Rol
        fields = (
            "betrokkene",
            "betrokkene_identificatie",
            "betrokkene_type",
            "indicatie_machtiging",
            "omschrijving",
            "omschrijving_generiek",
            "registratiedatum",
            "roltoelichting",
            "roltype",
            "url",
            "zaak",
        )


class ZaakObjectGroupSerializer(APIModelSerializer):
    items = serializers.ListField(
        child=serializers.JSONField(),
        help_text=_(
            "Collection of object-type specific items. "
            "The schema is determined by the upstream API(s). "
            "Each item has `zaakobjectUrl` attribute which is the url of case-object "
            "relations in ZAKEN API and should be used to change/delete the relations. "
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


class VertrouwelijkheidsAanduidingSerializer(APIModelSerializer):
    label = serializers.CharField(help_text=_("Human readable label of classication"))
    value = serializers.CharField(help_text=_("Value of classication"))

    class Meta:
        model = VertrouwelijkheidsAanduidingData
        fields = ("label", "value")


class UserAtomicPermissionSerializer(serializers.ModelSerializer):
    permissions = AtomicPermissionSerializer(
        many=True,
        source="zaak_atomic_permissions",
        help_text=_("Atomic permissions for the case"),
    )

    class Meta:
        model = User
        fields = ("username", "permissions")


class ObjecttypeProxySerializer(ProxySerializer):
    PROXY_SCHEMA_BASE = settings.OBJECTTYPES_API_SCHEMA
    PROXY_SCHEMA = ("/api/v1/objecttypes/", "get")
    PROXY_SCHEMA_PATH = ["components", "schemas", "ObjectType"]


class ObjecttypeVersionProxySerializer(ProxySerializer):
    PROXY_SCHEMA_BASE = settings.OBJECTTYPES_API_SCHEMA
    PROXY_SCHEMA_PATH = ["components", "schemas", "ObjectVersion"]


class ObjectProxySerializer(ProxySerializer):
    PROXY_SCHEMA_BASE = settings.OBJECTS_API_SCHEMA
    PROXY_SCHEMA_PATH = ["components", "schemas", "Object"]


class ObjectFilterProxySerializer(ProxySerializer):
    PROXY_SCHEMA_BASE = settings.OBJECTS_API_SCHEMA
    PROXY_SCHEMA_PATH = [
        "paths",
        "/objects/search",
        "post",
        "requestBody",
        "content",
        "application/json",
        "schema",
    ]


class ZaakObjectProxySerializer(ProxySerializer):
    PROXY_SCHEMA_BASE = settings.ZRC_API_SCHEMA
    PROXY_SCHEMA_PATH = ["components", "schemas", "ZaakObject"]
