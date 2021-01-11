from typing import List, Optional

from django.utils.translation import gettext as _

from rest_framework import serializers
from zgw_consumers.drf.serializers import APIModelSerializer

from zac.contrib.kownsl.data import (
    Advice,
    AdviceDocument,
    Approval,
    Author,
    ReviewRequest,
)


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
