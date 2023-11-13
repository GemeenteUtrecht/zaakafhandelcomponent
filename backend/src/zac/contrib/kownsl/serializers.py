from typing import Dict

from django.conf import settings
from django.utils.translation import gettext as _

from furl import furl
from rest_framework import serializers
from zgw_consumers.drf.serializers import APIModelSerializer

from zac.accounts.api.serializers import GroupSerializer, UserSerializer
from zac.api.polymorphism import PolymorphicSerializer
from zac.api.proxy import ProxySerializer
from zac.contrib.dowc.constants import DocFileTypes
from zac.contrib.dowc.utils import get_dowc_url_from_obj, get_dowc_url_from_vars
from zac.core.api.serializers import ZaakSerializer

from .constants import KownslTypes
from .data import Advice, AdviceDocument, Approval, Author, OpenReview, ReviewRequest


class KownslZaakDocumentSerializer(ProxySerializer):
    PROXY_SCHEMA_BASE = settings.EXTERNAL_API_SCHEMAS["KOWNSL_API_SCHEMA"]
    PROXY_SCHEMA_PATH = [
        "components",
        "schemas",
        "ZaakDocument",
    ]
    read_url = serializers.SerializerMethodField(
        help_text=_(
            "URL to read document. Opens the appropriate Microsoft Office application."
        )
    )
    write_url = serializers.SerializerMethodField(
        help_text=_(
            "URL to write document. Opens the appropriate Microsoft Office application."
        )
    )

    def get_read_url(self, obj: Dict) -> str:
        return get_dowc_url_from_vars(
            obj["bronorganisatie"], obj["identificatie"], purpose=DocFileTypes.read
        )

    def get_write_url(self, obj: Dict) -> str:
        return get_dowc_url_from_vars(
            obj["bronorganisatie"], obj["identificatie"], purpose=DocFileTypes.write
        )


class KownslReviewRequestSerializer(ProxySerializer):
    PROXY_SCHEMA_BASE = settings.EXTERNAL_API_SCHEMAS["KOWNSL_API_SCHEMA"]
    PROXY_SCHEMA_PATH = [
        "paths",
        "/api/v1/review-requests/{uuid}",
        "get",
        "responses",
        200,
        "content",
        "application/json",
        "schema",
    ]
    zaak = ZaakSerializer()
    zaakDocuments = KownslZaakDocumentSerializer(
        help_text=_("The documents with their download url and relevant metadata."),
        many=True,
    )


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


class ZaakRevReqSummarySerializer(APIModelSerializer):
    completed = serializers.IntegerField(
        label=_("completed requests"), help_text=_("The number of completed requests.")
    )
    can_lock = serializers.SerializerMethodField(
        label=_("can lock request"), help_text=_("User can lock the review request.")
    )

    class Meta:
        model = ReviewRequest
        fields = (
            "id",
            "review_type",
            "completed",
            "num_assigned_users",
            "can_lock",
            "locked",
            "lock_reason",
            "is_being_reconfigured",
        )

    def get_can_lock(self, obj) -> bool:
        if (
            request := self.context.get("request")
        ) and request.user.username == obj.requester["username"]:
            return True
        return False


class AuthorSerializer(APIModelSerializer):
    full_name = serializers.CharField(source="get_full_name")

    class Meta:
        model = Author
        fields = ("first_name", "last_name", "username", "full_name")


class ApprovalSerializer(APIModelSerializer):
    author = AuthorSerializer(
        label=_("author"),
        help_text=_("Author of review."),
    )
    status = serializers.SerializerMethodField(help_text=_("Status of approval."))

    class Meta:
        model = Approval
        fields = ("created", "author", "status", "toelichting", "group")

    def get_status(self, obj) -> str:
        if obj.approved:
            return _("Akkoord")
        else:
            return _("Niet Akkoord")


class AdviceDocumentSerializer(APIModelSerializer):
    advice_url = serializers.SerializerMethodField(
        help_text=_("URL-reference to the advice version of the document on the DoWC.")
    )
    source_url = serializers.SerializerMethodField(
        help_text=_("URL-reference to the source version of the document on the DoWC.")
    )
    title = serializers.CharField(
        source="document.bestandsnaam", help_text=_("The name of the document.")
    )
    download_advice_url = serializers.SerializerMethodField(
        help_text=_(
            "URL-reference to download the advice version of the document from the DoWC."
        )
    )
    download_source_url = serializers.SerializerMethodField(
        help_text=_(
            "URL-reference to download the source version of the document on the DoWC."
        )
    )

    class Meta:
        model = AdviceDocument
        fields = (
            "advice_url",
            "advice_version",
            "download_advice_url",
            "download_source_url",
            "source_url",
            "source_version",
            "title",
        )
        extra_kwargs = {
            "source_version": {
                "help_text": _("The version of the document before advice is given"),
            },
            "advice_version": {
                "help_text": _("The version of the document after advice is given.")
            },
        }

    def get_url(self, obj, args, purpose: str = DocFileTypes.read) -> str:
        url = furl(get_dowc_url_from_obj(obj.document, purpose=purpose))
        url.args = args
        return url.url

    def get_advice_url(self, obj) -> str:
        return self.get_url(obj, {"versie": obj.advice_version})

    def get_source_url(self, obj) -> str:
        return self.get_url(obj, {"versie": obj.source_version})

    def get_download_advice_url(self, obj) -> str:
        return self.get_url(
            obj, {"versie": obj.advice_version}, purpose=DocFileTypes.download
        )

    def get_download_source_url(self, obj) -> str:
        return self.get_url(
            obj, {"versie": obj.source_version}, purpose=DocFileTypes.download
        )


class AdviceSerializer(APIModelSerializer):
    author = AuthorSerializer(
        label=_("author"),
        help_text=_("Author of review."),
    )
    documents = AdviceDocumentSerializer(
        label=_("advice documents"),
        help_text=_("Documents relevant to the advice."),
        many=True,
    )

    class Meta:
        model = Advice
        fields = ("created", "author", "advice", "documents", "group")
        extra_kwargs = {
            "created": {"help_text": _("Date review request was created.")},
            "advice": {"help_text": _("Advice given for review request.")},
            "documents": {"help_text": _("URL-references of documents.")},
            "group": {"help_text": _("Group that advice was given by.")},
        }


class AdviceReviewsSerializer(serializers.Serializer):
    advices = AdviceSerializer(many=True, source="get_reviews_detail")


class ApprovalReviewsSerializer(serializers.Serializer):
    approvals = ApprovalSerializer(many=True, source="get_reviews_detail")


class OpenReviewUserSerializer(UserSerializer):
    class Meta(UserSerializer.Meta):
        model = UserSerializer.Meta.model
        fields = ("full_name",)


class OpenReviewGroupSerializer(GroupSerializer):
    class Meta(GroupSerializer.Meta):
        model = GroupSerializer.Meta.model
        fields = ("name",)


class OpenReviewSerializer(APIModelSerializer):
    deadline = serializers.DateField(
        help_text=_("Deadline date of open review request."), required=True
    )
    users = OpenReviewUserSerializer(
        many=True,
        read_only=True,
        help_text=_("`full_name` of the users assigned to review."),
        allow_null=True,
    )
    groups = OpenReviewGroupSerializer(
        many=True,
        read_only=True,
        help_text=_("`name` of the groups assigned to review."),
        allow_null=True,
    )

    class Meta:
        model = OpenReview
        fields = (
            "deadline",
            "users",
            "groups",
        )


class ZaakRevReqDetailSerializer(PolymorphicSerializer):
    serializer_mapping = {
        KownslTypes.advice: AdviceReviewsSerializer,
        KownslTypes.approval: ApprovalReviewsSerializer,
    }
    discriminator_field = "review_type"

    id = serializers.UUIDField(help_text=_("The `id` of the review request."))
    review_type = serializers.ChoiceField(
        choices=KownslTypes.choices, help_text=_("The review type.")
    )
    open_reviews = OpenReviewSerializer(many=True, read_only=True)
    is_being_reconfigured = serializers.BooleanField(
        help_text=_(
            "Boolean flag to indicate if review request is currently being reconfigured."
        ),
        required=True,
    )
