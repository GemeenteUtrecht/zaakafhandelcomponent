from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List

from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.api_models.zaken import Zaak
from zgw_consumers.drf.serializers import APIModelSerializer

from zac.accounts.models import User
from zac.api.context import get_zaak_context
from zac.camunda.data import Task
from zac.camunda.user_tasks import Context, register, usertask_context_serializer
from zac.core.api.fields import SelectDocumentsField
from zac.core.camunda.select_documents.serializers import DocumentSerializer
from zac.core.utils import get_ui_url

from .api import create_review_request
from .constants import FORM_KEY_REVIEW_TYPE_MAPPING, KownslTypes


@dataclass
class AdviceApprovalContext(Context):
    title: str
    zaak_informatie: Zaak
    documents: List[Document]
    review_type: str


class ZaakInformatieTaskSerializer(APIModelSerializer):
    class Meta:
        model = Zaak
        fields = (
            "omschrijving",
            "toelichting",
        )


class DocumentUserTaskSerializer(DocumentSerializer):
    class Meta:
        model = Document
        fields = (
            "beschrijving",
            "bestandsnaam",
            "read_url",
            "url",
        )


@usertask_context_serializer
class AdviceApprovalContextSerializer(APIModelSerializer):
    documents = DocumentUserTaskSerializer(many=True)
    zaak_informatie = ZaakInformatieTaskSerializer()
    review_type = serializers.ChoiceField(
        choices=KownslTypes.choices,
    )

    class Meta:
        model = AdviceApprovalContext
        fields = ("documents", "title", "zaak_informatie", "review_type")


#
# Write serializers
#


@dataclass
class SelectUsersRevReq:
    users: List[str]
    deadline: date


class SelectUsersRevReqSerializer(APIModelSerializer):
    """
    Select users and assign deadlines to those users in the configuration of
    review requests such as the advice and approval review requests.
    """

    users = serializers.ListField(child=serializers.CharField())
    deadline = serializers.DateField(
        input_formats=["%Y-%m-%d"],
    )

    class Meta:
        model = SelectUsersRevReq
        fields = (
            "users",
            "deadline",
        )

    def validate_users(self, users):
        """
        Validates that users are unique and exist.
        """
        # Check if users are unique.
        if len(users) > len(set(users)):
            raise serializers.ValidationError("Users need to be unique.")

        # Check if users exist.
        usernames = User.objects.all().values_list("username", flat=True)
        invalid_usernames = [user for user in users if user not in usernames]
        if invalid_usernames:
            raise serializers.ValidationError(
                f"Users {invalid_usernames} do not exist."
            )
        return users


@dataclass
class ConfigureReviewRequest:
    assigned_users: List[SelectUsersRevReq]
    selected_documents: List[str]
    toelichting: str


class ConfigureReviewRequestSerializer(APIModelSerializer):
    """
    This serializes configure review requests such as
    advice and approval review requests.

    Must have a ``task`` and ``request`` in its ``context``.
    """

    assigned_users = SelectUsersRevReqSerializer(many=True)
    selected_documents = SelectDocumentsField()
    toelichting = serializers.CharField(
        label=_("Toelichting"),
        allow_blank=True,
    )

    class Meta:
        model = ConfigureReviewRequest
        fields = (
            "assigned_users",
            "selected_documents",
            "toelichting",
        )

    def get_zaak_from_context(self):
        zaak_context = get_zaak_context(self.context["task"])
        return zaak_context.zaak

    def validate_assigned_users(self, assigned_users) -> List:
        """
        Validate that:
            assigned users are unique,
            at least 1 user is selected per step, and
            deadlines monotonically increase per step.
        """
        users_list = []
        for data in assigned_users:
            users = data["users"]
            if not users:
                raise serializers.ValidationError(
                    _("Please select at least 1 user."),
                    code="empty-users",
                )

            if any([user in users_list for user in users]):
                raise serializers.ValidationError(
                    _(
                        "Users in a serial review request process need to be unique. Please select unique users."
                    ),
                    code="unique-users",
                )

            users_list.extend(users)

        deadline_old = date.today() - timedelta(days=1)
        for data in assigned_users:
            deadline_new = data["deadline"]
            if deadline_new and not deadline_new > deadline_old:
                raise serializers.ValidationError(
                    _(
                        "Deadlines are not allowed to be equal in a serial review request "
                        "process but need to have at least 1 day in between them. "
                        "Please select a date greater than {minimum_date}."
                    ).format(minimum_date=deadline_old.strftime("%Y-%m-%d")),
                    code="invalid-date",
                )
            deadline_old = deadline_new

        return assigned_users

    def on_task_submission(self) -> None:
        """
        On task submission create the review request in the kownsl.
        """
        assert self.is_valid(), "Serializer must be valid"

        count_users = sum(
            [
                len(data["users"])
                for data in self.validated_data["assigned_users"]
                if data
            ]
        )

        user_deadlines = {
            user: str(data["deadline"])
            for data in self.validated_data["assigned_users"]
            for user in data["users"]
        }

        # Derive review_type from task.form_key
        review_type = FORM_KEY_REVIEW_TYPE_MAPPING[self.context["task"].form_key]
        zaak_context = get_zaak_context(self.context["task"])
        self.review_request = create_review_request(
            zaak_context.zaak.url,
            documents=self.validated_data["selected_documents"],
            review_type=review_type,
            num_assigned_users=count_users,
            toelichting=self.validated_data["toelichting"],
            user_deadlines=user_deadlines,
            requester=self.context["request"].user.username,
        )

    def get_process_variables(self) -> Dict[str, List]:
        """
        Get the required BPMN process variables for the BPMN.
        """
        # Assert is_valid has been called so that we can access validated data.
        assert hasattr(
            self, "review_request"
        ), "Must call on_task_submission before getting process variables."

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


@register(
    "zac:configureAdviceRequest",
    AdviceApprovalContextSerializer,
    ConfigureReviewRequestSerializer,
)
def get_advice_context(task: Task) -> AdviceApprovalContext:
    zaak_context = get_zaak_context(task, require_zaaktype=True, require_documents=True)
    return AdviceApprovalContext(
        documents=zaak_context.documents,
        review_type=KownslTypes.advice,
        title=f"{zaak_context.zaaktype.omschrijving} - {zaak_context.zaaktype.versiedatum}",
        zaak_informatie=zaak_context.zaak,
    )


@register(
    "zac:configureApprovalRequest",
    AdviceApprovalContextSerializer,
    ConfigureReviewRequestSerializer,
)
def get_approval_context(task: Task) -> AdviceApprovalContext:
    zaak_context = get_zaak_context(task, require_zaaktype=True, require_documents=True)
    return AdviceApprovalContext(
        documents=zaak_context.documents,
        review_type=KownslTypes.approval,
        title=f"{zaak_context.zaaktype.omschrijving} - {zaak_context.zaaktype.versiedatum}",
        zaak_informatie=zaak_context.zaak,
    )
