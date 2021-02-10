from datetime import date, timedelta
from typing import Dict, List, Optional

from django.core.validators import URLValidator
from django.utils.translation import gettext as _

from rest_framework import serializers
from zgw_consumers.drf.serializers import APIModelSerializer

from zac.accounts.models import User
from zac.api.proxy import ProxySerializer
from zac.camunda.process_instances import get_process_instance
from zac.camunda.user_tasks.api import get_task
from zac.core.api.serializers import ZaakSerializer
from zac.core.camunda import get_process_zaak_url
from zac.core.forms import _repr
from zac.core.services import get_documenten, get_zaak
from zac.core.utils import get_ui_url

from .api import create_review_request
from .constants import KownslTypes
from .data import Advice, AdviceDocument, Approval, Author, ReviewRequest


class KownslReviewRequestSerializer(ProxySerializer):
    PROXY_SCHEMA_BASE = "https://kownsl.utrechtproeftuin.nl/api/v1"
    PROXY_SCHEMA = ("/api/v1/review-requests/{uuid}", "get")
    zaak = ZaakSerializer()


class ZaakRevReqSummarySerializer(APIModelSerializer):
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
        fields = ("first_name", "last_name", "username")


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
        if obj.review_type == KownslTypes.advice:
            return AdviceSerializer(obj.advices, many=True).data
        else:
            return ApprovalSerializer(obj.approvals, many=True).data
