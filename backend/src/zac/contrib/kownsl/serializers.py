from datetime import date, timedelta
from typing import Dict, List, Optional

from django.core.validators import URLValidator
from django.utils.translation import gettext as _

from rest_framework import serializers
from zgw_consumers.drf.serializers import APIModelSerializer

from zac.accounts.models import User
from zac.camunda.process_instances import get_process_instance
from zac.camunda.user_tasks.api import get_task
from zac.core.camunda import get_process_zaak_url
from zac.core.services import fetch_zaaktype, get_documenten, get_zaak
from zac.core.utils import get_ui_url

from .api import create_review_request
from .constants import KownslTypes
from .data import Advice, AdviceDocument, Approval, Author, ReviewRequest


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


class SelectUsersRevReqSerializer(serializers.Serializer):
    """
    TODO: Write tests.
    """

    users = serializers.ListField(child=serializers.CharField())
    deadline = serializers.DateField(
        input_formats=["%Y-%m-%d"],
    )

    def validate_users(self, users):
        # Check if users are unique.
        if len(users) > len(set(users)):
            raise serializers.ValidationError("Users need to be unique.")

        # Check if users exist.
        usernames = User.objects.all().values_list("username", flat=True)
        invalid_usernames = [user not in usernames for user in users]
        if invalid_usernames:
            raise serializers.ValidationError(
                f"Users {invalid_usernames} do not exist."
            )
        return value


class ConfigureReviewRequestSerializer(serializers.Serializer):
    """
    TODO: Write tests.
    """

    assigned_users = SelectUsersRevReqSerializer(many=True)
    selected_documents = serializers.MultipleChoiceField(
        choices=(),
        validators=[URLValidator],
    )
    review_type = serializers.ChoiceField(choices=KownslTypes.choices)
    toelichting = serializers.CharField()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Get zaak documents to verify valid document selection
        task_id = kwargs["task_id"]
        self.task = get_task(task_id)
        process_instance = get_process_instance(self.task.process_instance_id)
        self.zaak_url = get_process_zaak_url(process_instance)
        zaak = get_zaak(zaak_url=self.zaak_url)
        documenten, _ = get_documenten(zaak)

        self.fields["selected_documents"].choices = [
            (doc.url, _repr(doc)) for doc in documenten
        ]

    def get_process_variables(self) -> Dict[str, List]:
        # Assert is_valid has been called so that we can access validated data.
        assert self.is_valid(), "Serializer must be valid"

        kownsl_frontend_url = get_ui_url(
            [
                "ui",
                "kownsl",
                "review-request",
                self.review_request.review_type,
            ],
            params={"uuid": self.review_request.id},
        )
        kownsl_users_list = [
            user
            for data in self.validated_data["assigned_users"]
            for user in data["users"]
        ]
        return {
            "kownslDocuments": self.validated_data["selected_documents"],
            "kownslUsersList": kownsl_users_list,
            "kownslReviewRequestId": str(self.review_request.id),
            "kownslFrontendUrl": kownsl_frontend_url,
        }

    def is_valid(self, raise_exception=True):
        super().is_valid(raise_exception=raise_exception)
        errors = self.validate_deadlines_monotonic_increasing()
        errors.extend(self.validate_users_are_unique())
        if errors:
            raise serializers.ValidationError(errors)

        return True

    def on_post(self):
        """
        On post in view do this.
        """
        count_users = sum(
            [
                len(data["users"])
                for data in self.validated_data["assigned_users"]
                if data
            ]
        )

        user_deadlines = {
            user["username"]: str(data["deadline"])
            for data in self.validated_data["assigned_users"]
            for users in data["users"]
        }

        self.review_request = create_review_request(
            self.zaak_url,
            documents=self.validated_data["selected_documents"],
            review_type=self.validated_data["review_type"],
            num_assigned_users=count_users,
            toelichting=self.validated_data["toelichting"],
            user_deadlines=user_deadlines,
            requester=self.context["request"].user.username,
        )

    def validate_deadlines_monotonic_increasing(self) -> bool:
        """
        Validate that deadlines per step are monotonic increasing
        """
        deadline_old = date.today() - timedelta(days=1)
        errors = []
        for data in self.validated_data["assigned_users"]:
            deadline_new = data["deadline"]
            if deadline_new and not deadline_new > deadline_old:
                errors.append(
                    serializers.ValidationError(
                        _(
                            "Deadlines are not allowed to be equal in a serial review request process but need to have at least 1 day in between them. Please select a date greater than {minimum_date}."
                        ).format(minimum_date=deadline_old.strftime("%Y-%m-%d")),
                        code="date-not-valid",
                    )
                )
            deadline_old = deadline_new
        return errors

    def validate_users_are_unique(self) -> bool:
        """
        Validate that users are unique and that at least 1 user is selected per step
        """
        users_list = []
        errors = []
        for data in self.validated_data["assigned_users"]:
            users = data["users"]
            if not users:
                errors.append(
                    serializers.ValidationError(
                        _("Please select at least 1 user."),
                        code="empty-user",
                    )
                )

            if any([user in users_list for user in users]):
                errors.append(
                    serializers.ValidationError(
                        _(
                            "Users in a serial review request process need to be unique. Please select unique users."
                        ),
                        code="unique-user",
                    )
                )

            users_list.extend(users)
        return errors
