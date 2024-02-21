from datetime import datetime
from typing import Dict, Union

from django.contrib.auth.models import Group
from django.urls import reverse_lazy
from django.utils.translation import gettext as _

from furl import furl
from rest_framework import serializers
from zgw_consumers.drf.serializers import APIModelSerializer

from zac.accounts.api.serializers import GroupSerializer, UserSerializer
from zac.accounts.models import Group, User
from zac.api.polymorphism import PolymorphicSerializer
from zac.contrib.dowc.constants import DocFileTypes
from zac.contrib.dowc.utils import get_dowc_url_from_obj
from zac.core.api.fields import SerializerSlugRelatedField
from zac.core.api.serializers import ZaakEigenschapSerializer, ZaakSerializer
from zac.elasticsearch.drf_api.serializers import ESListZaakDocumentSerializer

from ..constants import KownslTypes
from ..data import (
    Advice,
    Approval,
    KownslZaakEigenschap,
    OpenReview,
    ReviewDocument,
    ReviewRequest,
)

###################################################
#                  Kownsl Users                   #
###################################################


class KownslUserSerializer(UserSerializer):
    full_name = serializers.SerializerMethodField(
        help_text=_("User-friendly full name of user.")
    )

    class Meta:
        model = UserSerializer.Meta.model
        fields = (
            "email",
            "first_name",
            "full_name",
            "last_name",
            "username",
        )

    def get_full_name(self, obj) -> str:
        full_name = ""
        if isinstance(obj, User):
            full_name = obj.get_full_name()
        else:
            full_name = obj.get("full_name")
        return full_name


class KownslGroupSerializer(GroupSerializer):
    full_name = serializers.SerializerMethodField(
        help_text=_("User-friendly full name of group.")
    )

    class Meta:
        model = GroupSerializer.Meta.model
        fields = ("full_name", "name")

    def get_full_name(self, obj: Union[Dict, Group]) -> str:
        full_name = ""
        if isinstance(obj, Group):
            full_name = super().get_full_name(obj)
        else:
            full_name = obj.get("full_name")
        return full_name


class KownslUserSerializerSlugRelatedField(SerializerSlugRelatedField):
    response_serializer = KownslUserSerializer


class KownslGroupSerializerSlugRelatedField(SerializerSlugRelatedField):
    response_serializer = KownslGroupSerializer


###################################################
#                 Reviews - read                  #
###################################################


class KownslZaakEigenschapSerializer(APIModelSerializer):
    class Meta:
        model = KownslZaakEigenschap
        fields = ("url", "naam", "waarde")


class ReviewDocumentSerializer(APIModelSerializer):
    review_url = serializers.SerializerMethodField(
        help_text=_("URL to read the review version of the document on the DoWC.")
    )
    bestandsnaam = serializers.CharField(
        source="document.bestandsnaam",
        help_text=_("The filename of the document."),
        read_only=True,
    )
    document = serializers.URLField(
        help_text=_(
            "URL-reference to document in DRC API,  including `?versie=` parameter"
        ),
        source="document.url",
    )
    download_review_url = serializers.SerializerMethodField(
        help_text=_("URL-reference to download the review version of the document.")
    )
    download_source_url = serializers.SerializerMethodField(
        help_text=_("URL-reference to download the source version of the document.")
    )
    source_url = serializers.SerializerMethodField(
        help_text=_("URL to read the source version of the document on the DoWC.")
    )
    edited_document = serializers.URLField(
        write_only=True,
        help_text=_(
            "URL-reference of document to DRC API, including `?versie=` parameter."
        ),
        required=False,
    )

    class Meta:
        model = ReviewDocument
        fields = (
            "review_url",
            "review_version",
            "bestandsnaam",
            "document",
            "download_review_url",
            "download_source_url",
            "edited_document",
            "source_url",
            "source_version",
        )
        extra_kwargs = {
            "source_version": {
                "help_text": _("The version of the document before review is given"),
                "read_only": True,
            },
            "review_version": {
                "help_text": _("The version of the document after review is given."),
                "read_only": True,
            },
        }

    def build_url(self, url: str, kwargs: Dict) -> str:
        if not url:
            return ""
        return furl(url).set(kwargs).url

    def get_review_url(self, obj) -> str:
        return self.build_url(
            get_dowc_url_from_obj(obj.document, purpose=DocFileTypes.read),
            {"versie": obj.review_version},
        )

    def get_source_url(self, obj) -> str:
        return self.build_url(
            get_dowc_url_from_obj(obj.document, purpose=DocFileTypes.read),
            {"versie": obj.source_version},
        )

    def get_download_review_url(self, obj) -> str:
        return self.build_url(
            reverse_lazy(
                "core:download-document",
                kwargs={
                    "bronorganisatie": obj.document.bronorganisatie,
                    "identificatie": obj.document.identificatie,
                },
            ),
            {"versie": obj.review_version} if obj.review_version else {},
        )

    def get_download_source_url(self, obj) -> str:
        return self.build_url(
            reverse_lazy(
                "core:download-document",
                kwargs={
                    "bronorganisatie": obj.document.bronorganisatie,
                    "identificatie": obj.document.identificatie,
                },
            ),
            {"versie": obj.source_version} if obj.source_version else {},
        )


class ApprovalSerializer(APIModelSerializer):
    author = KownslUserSerializerSlugRelatedField(
        slug_field="username",
        queryset=User.objects.all(),
        required=True,
        help_text=_(
            "`username` of the author that approved. Automatically derived from request."
        ),
    )
    created = serializers.DateTimeField(
        help_text=_("Datetime review request was created."),
        default=lambda: datetime.now(),
    )
    group = KownslGroupSerializerSlugRelatedField(
        slug_field="name",
        queryset=Group.objects.all(),
        required=False,
        help_text=_("`name` of the group that author answered for."),
        allow_null=True,
        allow_empty=True,
    )
    review_documents = ReviewDocumentSerializer(
        label=_("review documents"),
        help_text=_("Documents relevant to the review."),
        many=True,
    )
    zaakeigenschappen = KownslZaakEigenschapSerializer(many=True)

    class Meta:
        model = Approval
        fields = (
            "author",
            "created",
            "group",
            "approved",
            "review_documents",
            "toelichting",
            "zaakeigenschappen",
        )
        extra_kwargs = {
            "approved": {"required": True},
            "toelichting": {"required": False},
        }


class AdviceSerializer(APIModelSerializer):
    author = KownslUserSerializerSlugRelatedField(
        slug_field="username",
        queryset=User.objects.all(),
        required=True,
        help_text=_("`username` of the author that adviced."),
    )
    created = serializers.DateTimeField(
        help_text=_("Datetime review request was created."),
        default=lambda: datetime.now(),
    )
    group = KownslGroupSerializerSlugRelatedField(
        slug_field="name",
        queryset=Group.objects.all(),
        required=False,
        help_text=_("`name` of the group that author answered for."),
        allow_null=True,
        allow_empty=True,
    )
    review_documents = ReviewDocumentSerializer(
        label=_("review documents"),
        help_text=_("Documents relevant to the review."),
        many=True,
    )
    zaakeigenschappen = KownslZaakEigenschapSerializer(many=True)

    class Meta:
        model = Advice
        fields = (
            "advice",
            "author",
            "created",
            "group",
            "review_documents",
            "zaakeigenschappen",
        )
        extra_kwargs = {
            "advice": {"help_text": _("Advice given for review request.")},
        }


class AdviceReviewsSerializer(serializers.Serializer):
    advices = AdviceSerializer(many=True, source="get_reviews")


class ApprovalReviewsSerializer(serializers.Serializer):
    approvals = ApprovalSerializer(many=True, source="get_reviews")


class OpenReviewSerializer(APIModelSerializer):
    deadline = serializers.DateField(
        help_text=_("Deadline date of open review request."), required=True
    )
    groups = serializers.ListField(
        read_only=True,
        child=serializers.CharField(
            help_text=_("`name` of the groups assigned to review."),
            allow_blank=True,
        ),
    )
    users = serializers.ListField(
        read_only=True,
        child=serializers.CharField(
            help_text=_("`full_name` of the users assigned to review."),
            allow_blank=True,
        ),
    )

    class Meta:
        model = OpenReview
        fields = (
            "deadline",
            "groups",
            "users",
        )


###################################################
#                 Reviews - write                 #
###################################################


class SubmitReviewDocumentSerializer(APIModelSerializer):
    document = serializers.URLField(
        help_text=_(
            "URL-reference to document in DRC API,  including `?versie=` parameter"
        )
    )
    edited_document = serializers.URLField(
        write_only=True,
        help_text=_(
            "URL-reference of document to DRC API, including `?versie=` parameter."
        ),
        required=False,
    )
    source_version = serializers.SerializerMethodField(
        help_text=_("The version of the document before review is given")
    )
    review_version = serializers.SerializerMethodField(
        help_text=_("The version of the document after review is given")
    )

    class Meta:
        model = ReviewDocument
        fields = (
            "document",
            "edited_document",
            "review_version",
            "source_version",
        )

    def get_source_version(self, obj: Dict) -> int:
        return int(furl(obj["document"]).args.get("versie"))

    def get_review_version(self, obj: Dict) -> int:
        url = obj.get("edited_document", obj["document"])
        return int(furl(url).args.get("versie"))

    def validate(self, attrs: dict):
        validated_data = super().validate(attrs)

        edited_document_url = validated_data.get("edited_document")
        if edited_document_url is None:
            edited_document_url = validated_data["document"]

        source_url = furl(validated_data["document"])
        review_url = furl(edited_document_url)
        # compare URLs without query
        if source_url.copy().remove("versie") != review_url.copy().remove("versie"):
            raise serializers.ValidationError(
                _("Source and review version must be versions of the same document")
            )

        source_version = source_url.args.get("versie")
        review_version = review_url.args.get("versie")

        errs = {}
        err_no_version = _("The URL is missing the '?versie=' querystring parameter.")
        err_invalid_version = _("The 'versie' parameter must be a positive integer.")
        for field, version in [
            ("document", source_version),
            ("edited_document", review_version),
        ]:
            # check if the version parameter is present
            if not version:
                errs[field] = err_no_version
                continue

            # check for valid ranges
            try:
                value = int(version)
            except (ValueError, TypeError):
                errs[field] = err_invalid_version
            else:
                if value <= 0:
                    errs[field] = err_invalid_version

        if errs:
            raise serializers.ValidationError(errs)

        return validated_data

    def to_representation(self, data):
        data = super().to_representation(data)
        if "edited_document" in data:
            del data["edited_document"]
        return data


class SubmitApprovalSerializer(APIModelSerializer):
    author = KownslUserSerializerSlugRelatedField(
        slug_field="username",
        queryset=User.objects.all(),
        required=True,
        help_text=_(
            "`username` of the author that approved. Automatically derived from request."
        ),
    )
    created = serializers.DateTimeField(
        help_text=_("Datetime review request was created."),
        default=lambda: datetime.now(),
    )
    group = KownslGroupSerializerSlugRelatedField(
        slug_field="name",
        queryset=Group.objects.all(),
        required=False,
        help_text=_("`name` of the group that author answered for."),
        allow_null=True,
    )
    review_documents = SubmitReviewDocumentSerializer(
        label=_("review documents"),
        help_text=_("Documents relevant to the review."),
        many=True,
        required=False,
    )
    zaakeigenschappen = KownslZaakEigenschapSerializer(many=True, required=False)

    class Meta:
        model = Approval
        fields = (
            "author",
            "created",
            "group",
            "approved",
            "toelichting",
            "review_documents",
            "zaakeigenschappen",
        )
        extra_kwargs = {
            "approved": {"required": True},
            "toelichting": {"required": False},
        }

    def validate_group(self, group):
        if not group:
            return ""
        return group

    def validate(self, data):
        if not data.get("zaakeigenschappen") and not data.get("review_documents"):
            raise serializers.ValidationError(
                _(
                    "At least one of: [`review_documents`, `zaakeigenschappen`] is required."
                )
            )

        return super().validate(data)


class SubmitAdviceSerializer(APIModelSerializer):
    author = KownslUserSerializerSlugRelatedField(
        slug_field="username",
        queryset=User.objects.all(),
        required=True,
        help_text=_("`username` of the author that adviced."),
    )
    created = serializers.DateTimeField(
        help_text=_("Datetime review request was created."),
        default=lambda: datetime.now(),
    )
    group = KownslGroupSerializerSlugRelatedField(
        slug_field="name",
        queryset=Group.objects.all(),
        required=False,
        help_text=_("`name` of the group that author answered for."),
        allow_null=True,
    )
    review_documents = SubmitReviewDocumentSerializer(
        label=_("review documents"),
        help_text=_("Documents relevant to the review."),
        many=True,
        required=False,
    )
    zaakeigenschappen = KownslZaakEigenschapSerializer(many=True, required=False)

    class Meta:
        model = Advice
        fields = (
            "advice",
            "author",
            "created",
            "group",
            "review_documents",
            "zaakeigenschappen",
        )
        extra_kwargs = {
            "advice": {"help_text": _("Advice given for review request.")},
        }

    def validate_group(self, group):
        if not group:
            return ""
        return group

    def validate(self, data):
        if not data.get("zaakeigenschappen") and not data.get("review_documents"):
            raise serializers.ValidationError(
                _(
                    "At least one of: [`review_documents`, `zaakeigenschappen`] is required."
                )
            )

        return super().validate(data)


###################################################
#              ReviewRequests - read              #
###################################################


class ZaakRevReqDetailSerializer(PolymorphicSerializer):
    serializer_mapping = {
        KownslTypes.advice: AdviceReviewsSerializer,
        KownslTypes.approval: ApprovalReviewsSerializer,
    }
    discriminator_field = "review_type"
    created = serializers.DateTimeField(
        help_text=_("Datetime review request was created.")
    )
    documents = serializers.ListField(
        child=serializers.URLField(
            help_text=_("URL-reference to related INFORMATIEOBJECT.")
        ),
        help_text=_("URL-references to related INFORMATIEOBJECTS."),
    )
    id = serializers.UUIDField(
        help_text=_("The `id` of the review request."), read_only=True
    )
    is_being_reconfigured = serializers.BooleanField(
        help_text=_(
            "Boolean flag to indicate if review request is currently being reconfigured."
        ),
        required=True,
    )
    locked = serializers.BooleanField(
        help_text=_("Boolean flag to indicate if review request is currently locked.")
    )
    lock_reason = serializers.CharField(
        help_text=_("Reason why review request is locked.")
    )
    open_reviews = OpenReviewSerializer(
        many=True, read_only=True, source="get_open_reviews"
    )
    requester = KownslUserSerializerSlugRelatedField(
        slug_field="username",
        queryset=User.objects.prefetch_related("groups").all(),
        required=True,
        help_text=_("`username` of user who requested review."),
    )
    review_type = serializers.ChoiceField(
        choices=KownslTypes.choices, help_text=_("The review type.")
    )
    zaak = ZaakSerializer(help_text=_("ZAAK related to review."))
    zaakeigenschappen = ZaakEigenschapSerializer(
        source="get_zaakeigenschappen", many=True, read_only=True
    )
    zaak_documents = ESListZaakDocumentSerializer(
        help_text=_("The supporting documents for the review."),
        many=True,
        read_only=True,
        source="get_zaak_documents",
    )


class ZaakRevReqSummarySerializer(APIModelSerializer):
    can_lock = serializers.SerializerMethodField(
        label=_("can lock request"), help_text=_("User can lock the review request.")
    )
    completed = serializers.IntegerField(
        label=_("completed requests"),
        help_text=_("The number of completed requests."),
        source="get_completed",
    )

    class Meta:
        model = ReviewRequest
        fields = (
            "can_lock",
            "completed",
            "id",
            "is_being_reconfigured",
            "locked",
            "lock_reason",
            "num_assigned_users",
            "review_type",
        )

    def get_can_lock(self, obj) -> bool:
        if (
            request := self.context.get("request")
        ) and request.user.username == obj.requester["username"]:
            return True
        return False

    def get_completed(self, obj) -> int:
        return len(obj.reviews)


###################################################
#              ReviewRequests - write             #
###################################################


class UpdateZaakReviewRequestSerializer(APIModelSerializer):
    update_users = serializers.BooleanField(
        required=False,
        help_text=_(
            "A boolean flag to indicate whether a change of users is requested in the review request. If review request is/will be locked - this will fail."
        ),
    )

    class Meta:
        model = ReviewRequest
        fields = ("lock_reason", "update_users")
        extra_kwargs = {
            "lock_reason": {
                "allow_blank": False,
                "required": False,
                "help_text": _(
                    "If the review request will be locked the users can not be updated."
                ),
            }
        }

    def validate(self, data):
        validated_data = super().validate(data)
        if validated_data.get("update_users") and validated_data.get("lock_reason"):
            raise serializers.ValidationError(
                _("A locked review request can not be updated.")
            )
        if validated_data.get("update_users"):
            # Set is_being_reconfigured field
            validated_data["is_being_reconfigured"] = True
        return validated_data
