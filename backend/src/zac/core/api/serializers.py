import pathlib
from datetime import date, datetime
from decimal import ROUND_05UP
from typing import Optional

from django.conf import settings
from django.core.validators import RegexValidator
from django.template.defaultfilters import filesizeformat
from django.utils.translation import gettext as _

from requests.exceptions import HTTPError
from rest_framework import serializers
from rest_framework.utils import formatting
from zds_client import ClientError
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
    RolTypes,
    VertrouwelijkheidsAanduidingen,
)
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.api_models.zaken import Resultaat, Status, ZaakEigenschap
from zgw_consumers.drf.serializers import APIModelSerializer

from zac.accounts.api.serializers import AtomicPermissionSerializer
from zac.accounts.models import User
from zac.api.polymorphism import PolymorphicSerializer, SerializerCls
from zac.api.proxy import ProxySerializer
from zac.camunda.api.utils import get_bptl_app_id_variable
from zac.camunda.processes import get_top_level_process_instances
from zac.contrib.dowc.constants import DocFileTypes
from zac.contrib.dowc.fields import DowcUrlFieldReadOnly
from zac.core.camunda.start_process.models import CamundaStartProcess
from zac.core.rollen import Rol
from zac.core.services import (
    fetch_rol,
    fetch_zaaktype,
    get_document,
    get_documenten,
    get_informatieobjecttypen_for_zaak,
    get_roltype,
    get_roltypen,
    get_statustypen,
    get_zaak,
    get_zaaktypen,
)
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
from .validators import ZaakFileValidator


class InformatieObjectTypeSerializer(APIModelSerializer):
    class Meta:
        model = InformatieObjectType
        fields = (
            "url",
            "omschrijving",
        )


class GetZaakDocumentSerializer(APIModelSerializer):
    read_url = DowcUrlFieldReadOnly(purpose=DocFileTypes.read)
    write_url = DowcUrlFieldReadOnly(purpose=DocFileTypes.write, allow_blank=True)
    vertrouwelijkheidaanduiding = serializers.CharField(
        source="get_vertrouwelijkheidaanduiding_display"
    )
    informatieobjecttype = InformatieObjectTypeSerializer()
    current_user_is_editing = serializers.SerializerMethodField()
    last_edited_date = serializers.SerializerMethodField()

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
            "last_edited_date",
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
        if "open_documenten" in self.context:
            if obj.url in self.context["open_documenten"]:
                return True
            else:
                return False
        return None

    def get_last_edited_date(self, obj) -> Optional[datetime]:
        if "editing_history" in self.context:
            return self.context["editing_history"][obj.url]
        return None


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
        help_text=_("URL-reference of the ZAAK"),
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
                _("The document is unrelated to {zaak}.").format(
                    zaak=zaak.identificatie
                )
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
        required=True,
        help_text=_("URL-reference to the main ZAAK in the ZAKEN API."),
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
                _("ZAAKen cannot be related to themselves.")
            )

        if data["aard_relatie"] == data["aard_relatie_omgekeerde_richting"]:
            raise serializers.ValidationError(
                _("The nature of the ZAAK-relations cannot be the same.")
            )

        return data


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
    zaaktype_omschrijving = serializers.CharField(
        required=True,
        help_text=_("`omschrijving` of ZAAKTYPE."),
    )
    zaaktype_catalogus = serializers.URLField(
        required=True,
        help_text=_("URL-reference to the CATALOGUS of ZAAKTYPE."),
    )
    zaaktype = serializers.HiddenField(default="")
    omschrijving = serializers.CharField(
        required=True, help_text=_("A short summary of the ZAAK.")
    )
    toelichting = serializers.CharField(
        help_text=_("A comment on the ZAAK."), default="", allow_blank=True
    )
    startdatum = serializers.DateField(
        default=date.today(), help_text=_("The date the ZAAK begins.")
    )

    def validate(self, data):
        validated_data = super().validate(data)
        zt_omschrijving = validated_data["zaaktype_omschrijving"]
        zt_catalogus = validated_data["zaaktype_catalogus"]
        zaaktypen = get_zaaktypen(catalogus=zt_catalogus, omschrijving=zt_omschrijving)
        if not zaaktypen:
            raise serializers.ValidationError(
                _(
                    "ZAAKTYPE {zt_omschrijving} can not be found in {zt_catalogus}."
                ).format(zt_omschrijving=zt_omschrijving, zt_catalogus=zt_catalogus)
            )
        max_date = max([zt.versiedatum for zt in zaaktypen])
        zaaktype = [zt for zt in zaaktypen if zt.versiedatum == max_date][0]
        validated_data["zaaktype"] = zaaktype.url
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
            "kan_geforceerd_bijwerken",
            "has_process",
            "is_static",
        )

    def get_kan_geforceerd_bijwerken(self, obj) -> bool:
        return CanForceEditClosedZaak().check_for_any_permission(
            self.context["request"], obj
        )

    def get_has_process(self, obj) -> bool:
        process_instances = get_top_level_process_instances(obj.url)
        # Filter out the process instance that started the zaak
        process_instances = [
            pi
            for pi in process_instances
            if pi.definition.key != settings.CREATE_ZAAK_PROCESS_DEFINITION_KEY
        ]
        return bool(process_instances)

    def get_is_static(self, obj) -> bool:
        zaaktype_catalogus = obj.zaaktype.catalogus
        zaaktype_identificatie = obj.zaaktype.identificatie
        objs = CamundaStartProcess.objects.filter(
            zaaktype_catalogus=zaaktype_catalogus,
            zaaktype_identificatie=zaaktype_identificatie,
        )
        return not objs.exists()


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
    )

    class Meta:
        model = ZaakEigenschap
        fields = ("waarde",)


class DateValueSerializer(APIModelSerializer):
    waarde = serializers.DateField(
        label=_("EIGENSCHAP value"),
        source="get_waarde",
    )

    class Meta:
        model = ZaakEigenschap
        fields = ("waarde",)


class DateTimeValueSerializer(APIModelSerializer):
    waarde = serializers.DateTimeField(
        label=_("EIGENSCHAP value"),
        source="get_waarde",
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
        extra_kwargs = {"url": {"read_only": True}}


class CreateZaakEigenschapSerializer(serializers.Serializer):
    naam = serializers.CharField(
        help_text=_(
            "Name of EIGENSCHAP. Must match EIGENSCHAP name as defined in CATALOGI API."
        )
    )
    waarde = serializers.CharField(
        help_text=_(
            "Value of ZAAKEIGENSCHAP. Must be able to be formatted as defined by the EIGENSCHAP spec."
        )
    )
    zaak_url = serializers.URLField(help_text=_("URL-reference to ZAAK."))


class UpdateZaakEigenschapWaardeSerializer(serializers.Serializer):
    waarde = serializers.CharField(
        help_text=_(
            "Value of ZAAKEIGENSCHAP. Must be formatted as defined by the EIGENSCHAP spec."
        )
    )


class RelatedZaakDetailSerializer(ZaakDetailSerializer):
    status = ZaakStatusSerializer()

    class Meta(ZaakDetailSerializer.Meta):
        fields = ZaakDetailSerializer.Meta.fields + ("status",)


class RelatedZaakSerializer(serializers.Serializer):
    aard_relatie = serializers.CharField()
    zaak = RelatedZaakDetailSerializer()


class RolTypeSerializer(APIModelSerializer):
    class Meta:
        model = RolType
        fields = ("url", "omschrijving", "omschrijving_generiek")


class ReadRolSerializer(APIModelSerializer):
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
                
                By default, all string fields are submitted with a blank string, i.e. ("")."""
            ),
        )

    name = f"{name}TaskDataSerializer"
    return type(name, (IdentificatieSerializer,), {})


class SetDefaultToEmptyStringMixin:
    def _set_field_to_default_empty_string(self, field):
        if isinstance(field, serializers.Serializer):
            for _field in field.fields:
                _field = self._set_field_to_default_empty_string(_field)
        if isinstance(field, serializers.CharField):
            field.default = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self._set_field_to_default_empty_string(self, field)


@betrokkene_identificatie_serializer
class RolNatuurlijkPersoonSerializer(SetDefaultToEmptyStringMixin, ProxySerializer):
    PROXY_SCHEMA_BASE = settings.EXTERNAL_API_SCHEMAS["ZRC_API_SCHEMA"]
    PROXY_SCHEMA_PATH = [
        "components",
        "schemas",
        "RolNatuurlijkPersoon",
    ]


@betrokkene_identificatie_serializer
class RolNietNatuurlijkPersoonSerializer(SetDefaultToEmptyStringMixin, ProxySerializer):
    PROXY_SCHEMA_BASE = settings.EXTERNAL_API_SCHEMAS["ZRC_API_SCHEMA"]
    PROXY_SCHEMA_PATH = [
        "components",
        "schemas",
        "RolNietNatuurlijkPersoon",
    ]


@betrokkene_identificatie_serializer
class RolVestigingSerializer(SetDefaultToEmptyStringMixin, ProxySerializer):
    PROXY_SCHEMA_BASE = settings.EXTERNAL_API_SCHEMAS["ZRC_API_SCHEMA"]
    PROXY_SCHEMA_PATH = [
        "components",
        "schemas",
        "RolVestiging",
    ]


@betrokkene_identificatie_serializer
class RolOrganisatorischeEenheidSerializer(
    SetDefaultToEmptyStringMixin, ProxySerializer
):
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
    roltoelichting = serializers.SerializerMethodField(
        help_text=_(
            "Comment related to the ROL. Usually it is the `omschrijving` of ROLTYPE of ROL."
        )
    )
    roltype = serializers.URLField(
        required=True, help_text=_("URL-reference to ROLTYPE of ROL.")
    )
    url = serializers.URLField(
        read_only=True, help_text=_("URL-reference to ROL itself.")
    )
    zaak = serializers.URLField(
        help_text=_("URL-reference to ZAAK of ROL."),
    )

    def get_roltoelichting(self, obj) -> str:
        rt = obj.roltype if isinstance(obj, Rol) else obj["roltype"]
        try:
            roltype = get_roltype(rt)
        except ClientError:
            raise serializers.ValidationError(
                _("Can not find ROLTYPE {rt}.").format(rt=rt)
            )
        return roltype.omschrijving

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
        if data["betrokkene"] and data["betrokkene_type"]:
            raise serializers.ValidationError(
                _("`betrokkene` and `betrokkene_type` are mutually exclusive.")
            )
        if data["betrokkene"] and data["betrokkene_identificatie"]:
            raise serializers.ValidationError(
                _("`betrokkene` and `betrokkene_identificatie` are mutually exclusive.")
            )
        return data


class DestroyRolSerializer(APIModelSerializer):
    url = serializers.URLField(
        required=True, help_text=_("URL-reference to ROL itself.")
    )

    class Meta:
        model = Rol
        fields = ("url",)

    def validate_url(self, url):
        try:
            zaak = self.context["zaak"]
        except KeyError:
            raise RuntimeError(
                _("Serializer {name} needs ZAAK in context.").format(name=self.__name__)
            )

        rol = fetch_rol(url)
        if not rol.zaak == zaak.url:
            raise serializers.ValidationError(_("ROL does not belong to ZAAK."))
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
        fields = ("catalogus", "omschrijving")
        extra_kwargs = {
            "omschrijving": {
                "help_text": _(
                    "Description of ZAAKTYPE, used as an aggregator of different versions of ZAAKTYPE"
                )
            }
        }


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
        help_text=_("Atomic permissions for the ZAAK"),
    )

    class Meta:
        model = User
        fields = ("username", "permissions")


class ObjecttypeProxySerializer(ProxySerializer):
    PROXY_SCHEMA_BASE = settings.EXTERNAL_API_SCHEMAS["OBJECTTYPES_API_SCHEMA"]
    PROXY_SCHEMA = ("/api/v1/objecttypes/", "get")
    PROXY_SCHEMA_PATH = ["components", "schemas", "ObjectType"]


class ObjecttypeVersionProxySerializer(ProxySerializer):
    PROXY_SCHEMA_BASE = settings.EXTERNAL_API_SCHEMAS["OBJECTTYPES_API_SCHEMA"]
    PROXY_SCHEMA_PATH = ["components", "schemas", "ObjectVersion"]


class ObjectProxySerializer(ProxySerializer):
    PROXY_SCHEMA_BASE = settings.EXTERNAL_API_SCHEMAS["OBJECTS_API_SCHEMA"]
    PROXY_SCHEMA_PATH = ["components", "schemas", "Object"]


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


class ZaakObjectProxySerializer(ProxySerializer):
    PROXY_SCHEMA_BASE = settings.EXTERNAL_API_SCHEMAS["ZRC_API_SCHEMA"]
    PROXY_SCHEMA_PATH = ["components", "schemas", "ZaakObject"]
