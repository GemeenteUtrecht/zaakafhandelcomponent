from typing import Any, List, Optional

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
from zgw_consumers.api_models.constants import AardRelatieChoices, RolTypes
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.api_models.zaken import Resultaat, Status, ZaakEigenschap
from zgw_consumers.drf.serializers import APIModelSerializer

from zac.contrib.kownsl.data import (
    Advice,
    AdviceDocument,
    Approval,
    Author,
    ReviewRequest,
)
from zac.core.rollen import Rol
from zgw.models.zrc import Zaak

from ..zaakobjecten import ZaakObjectGroup
from .utils import (
    CSMultipleChoiceField,
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
    download_url = serializers.SerializerMethodField()

    def get_bestandsgrootte(self, obj):
        return filesizeformat(obj.bestandsomvang)

    def get_download_url(self, obj):
        path = reverse(
            "core:download-document",
            kwargs={
                "bronorganisatie": obj.bronorganisatie,
                "identificatie": obj.identificatie,
            },
        )
        return self.context["request"].build_absolute_uri(path)


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


class ZaakIdentificatieSerializer(serializers.Serializer):
    identificatie = serializers.CharField(required=True)


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
        )


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


class ResultaatTypeSerializer(APIModelSerializer):
    class Meta:
        model = ResultaatType
        fields = ("url", "omschrijving")


class ResultaatSerializer(APIModelSerializer):
    resultaattype = ResultaatTypeSerializer()

    class Meta:
        model = Resultaat
        fields = ("url", "resultaattype", "toelichting")


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


class ZaakEigenschapSerializer(APIModelSerializer):
    value = serializers.SerializerMethodField(
        label=_("property value"),
        help_text=_("The backing data type depens on the eigenschap format."),
    )
    eigenschap = EigenschapSerializer()

    class Meta:
        model = ZaakEigenschap
        fields = (
            "url",
            "eigenschap",
            "value",
        )

    def get_value(self, obj) -> Any:
        return obj.get_waarde()


class DocumentTypeSerializer(APIModelSerializer):
    class Meta:
        model = InformatieObjectType
        fields = (
            "url",
            "omschrijving",
        )


class ZaakDocumentSerializer(APIModelSerializer):
    download_url = serializers.SerializerMethodField(
        label=_("ZAC download URL"),
        help_text=_(
            "The download URL for the end user. Will serve the file as attachment."
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
            "download_url",
        )
        extra_kwargs = {
            "bestandsomvang": {
                "help_text": _("File size in bytes"),
            }
        }

    def get_download_url(self, obj) -> str:
        path = reverse(
            "core:download-document",
            kwargs={
                "bronorganisatie": obj.bronorganisatie,
                "identificatie": obj.identificatie,
            },
        )
        return self.context["request"].build_absolute_uri(path)


class RelatedZaakDetailSerializer(ZaakDetailSerializer):
    status = ZaakStatusSerializer()
    resultaat = ResultaatSerializer()

    class Meta(ZaakDetailSerializer.Meta):
        fields = ZaakDetailSerializer.Meta.fields + ("status", "resultaat")


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


class ZaakRevReqCompletedSerializer(APIModelSerializer):
    completed = serializers.SerializerMethodField(
        label=_("completed requests"), help_text=_("The number of completed requests.")
    )

    class Meta:
        model = ReviewRequest
        fields = ("id", "review_type", "completed", "num_assigned_users")

    def get_completed(self, obj) -> int:
        return obj.num_advices + obj.num_approvals


class AuthorSerializer(APIModelSerializer):
    class Meta:
        model = Author
        fields = ("first_name", "last_name")


class ApprovalSerializer(APIModelSerializer):
    author = AuthorSerializer(
        label=_("author"),
        help_text=_("Author of review."),
    )
    status = serializers.SerializerMethodField(help_text=_("Status of approval."))

    class Meta:
        model = Approval
        fields = ("created", "author", "status", "toelichting")

    def get_status(self, obj):
        if obj.approved:
            return _("Akkoord")
        else:
            return _("Niet Akkoord")


class DocumentSerializer(APIModelSerializer):
    class Meta:
        model = AdviceDocument
        fields = ("document", "source_version", "advice_version")


class AdviceSerializer(APIModelSerializer):
    author = AuthorSerializer(
        label=_("author"),
        help_text=_("Author of review."),
    )
    documents = DocumentSerializer(
        label=_("Advice documents"),
        help_text=_("Documents relevant to the advice."),
        many=True,
    )

    class Meta:
        model = Advice
        fields = ("created", "author", "advice", "documents")


class ZaakRevReqDetailSerializer(APIModelSerializer):
    reviews = serializers.SerializerMethodField()

    class Meta:
        model = ReviewRequest
        fields = ("id", "review_type", "reviews")

    def get_reviews(self, obj) -> Optional[List[dict]]:
        if obj.review_type == "advice":
            return AdviceSerializer(obj.advices, many=True).data
        else:
            return ApprovalSerializer(obj.approvals, many=True).data
