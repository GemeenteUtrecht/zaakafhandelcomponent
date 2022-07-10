from django.conf import settings
from django.utils.translation import gettext as _

from furl import furl
from rest_framework import serializers
from zgw_consumers.drf.serializers import APIModelSerializer

from zac.api.polymorphism import PolymorphicSerializer
from zac.api.proxy import ProxySerializer
from zac.contrib.dowc.constants import DocFileTypes
from zac.contrib.dowc.utils import get_dowc_url
from zac.core.api.serializers import ZaakSerializer

from .constants import KownslTypes
from .data import Advice, AdviceDocument, Approval, Author, ReviewRequest


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


class LockReviewRequestSerializer(APIModelSerializer):
    class Meta:
        model = ReviewRequest
        fields = ("lock_reason",)
        extra_kwargs = {"lock_reason": {"allow_blank": False, "required": True}}


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
        )

    def get_can_lock(self, obj) -> bool:
        if (
            request := self.context.get("request")
        ) and request.user.username == obj.requester["username"]:
            return True
        return False


class AuthorSerializer(APIModelSerializer):
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

    class Meta:
        model = AdviceDocument
        fields = (
            "advice_url",
            "advice_version",
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

    def get_url(self, obj, args) -> str:
        url = furl(get_dowc_url(obj.document, purpose=DocFileTypes.read))
        url.args = args
        return url.url

    def get_advice_url(self, obj) -> str:
        return self.get_url(obj, {"versie": obj.advice_version})

    def get_source_url(self, obj) -> str:
        return self.get_url(obj, {"versie": obj.source_version})


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
    advices = AdviceSerializer(many=True)


class ApprovalReviewsSerializer(serializers.Serializer):
    approvals = ApprovalSerializer(many=True)


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
