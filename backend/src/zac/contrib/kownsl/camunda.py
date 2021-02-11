from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, NoReturn

from django.core.validators import URLValidator
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from rest_framework import serializers
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.api_models.zaken import Zaak
from zgw_consumers.drf.serializers import APIModelSerializer

from zac.accounts.models import User
from zac.camunda.data import Task
from zac.camunda.process_instances import get_process_instance
from zac.camunda.user_tasks import Context, register, usertask_context_serializer
from zac.contrib.dowc.constants import DocFileTypes
from zac.contrib.kownsl.constants import KownslTypes
from zac.core.camunda import get_process_zaak_url
from zac.core.services import fetch_zaaktype, get_documenten, get_zaak
from zac.core.utils import get_ui_url

from .api import create_review_request


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


class DocumentUserTaskSerializer(APIModelSerializer):
    read_url = serializers.SerializerMethodField(
        label=_("ZAC document read URL"),
        help_text=_(
            "A URL that on POST request returns a magicUrl to the document on a webdav server."
        ),
    )

    class Meta:
        model = Document
        fields = (
            "beschrijving",
            "bestandsnaam",
            "read_url",
            "url",
        )

    def get_read_url(self, obj) -> str:
        """
        Create the document read url to facilitate opening the document
        in a MS WebDAV client.
        """
        return reverse(
            "dowc:request-doc",
            kwargs={
                "bronorganisatie": obj.bronorganisatie,
                "identificatie": obj.identificatie,
                "purpose": DocFileTypes.read,
            },
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

    Must have a ``task`` in its ``context``.
    """

    assigned_users = SelectUsersRevReqSerializer(many=True)
    selected_documents = serializers.MultipleChoiceField(
        choices=(),
        validators=[URLValidator],
        label=_("Selecteer de relevante documenten"),
        help_text=_(
            "Dit zijn de documenten die bij de zaak horen. Selecteer de relevante "
            "documenten voor het vervolg van het proces."
        ),
    )
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Get zaak documents to verify valid document selection
        task = self.context.get("task")
        process_instance = get_process_instance(task.process_instance_id)
        self.zaak_url = get_process_zaak_url(process_instance)
        zaak = get_zaak(zaak_url=self.zaak_url)
        documenten, rest = get_documenten(zaak)

        self.fields["selected_documents"].choices = [
            (doc.url, doc.url) for doc in documenten
        ]

    def validate_deadlines_monotonic_increasing(self) -> bool:
        """
        Validate that deadlines per step are monotonic increasing.
        """
        deadline_old = date.today() - timedelta(days=1)
        errors = []
        for data in self.validated_data["assigned_users"]:
            deadline_new = data["deadline"]
            if deadline_new and not deadline_new > deadline_old:
                errors.append(
                    serializers.ValidationError(
                        _(
                            "Deadlines are not allowed to be equal in a serial review request "
                            "process but need to have at least 1 day in between them. "
                            "Please select a date greater than {minimum_date}."
                        ).format(minimum_date=deadline_old.strftime("%Y-%m-%d")),
                        code="date-not-valid",
                    )
                )
            deadline_old = deadline_new
        return errors

    def validate_users_are_unique(self) -> bool:
        """
        Validate that users are unique and that at least 1 user is selected per step.
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

    def is_valid(self, raise_exception=True):
        super().is_valid(raise_exception=raise_exception)
        errors = self.validate_deadlines_monotonic_increasing()
        errors.extend(self.validate_users_are_unique())
        if errors:
            raise serializers.ValidationError(errors)

        return True

    def on_task_submission(self) -> NoReturn:
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

        if KownslTypes.advice.lower() in self.context["task"].form_key.lower():
            review_type = KownslTypes.advice
        else:
            review_type = KownslTypes.approval

        self.review_request = create_review_request(
            self.zaak_url,
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


def get_advice_approval_context(task: Task) -> dict:
    """
    Creates the part of the context that advices and approvals have in common.
    """
    process_instance = get_process_instance(task.process_instance_id)
    zaak_url = get_process_zaak_url(process_instance)
    zaak = get_zaak(zaak_url=zaak_url)
    zaaktype = fetch_zaaktype(zaak.zaaktype)
    documents = get_documenten(zaak)
    return {
        "zaak_informatie": process_instance,
        "title": f"{zaaktype.omschrijving} - {zaaktype.versiedatum}",
        "documents": documents,
    }


# Refactoring get_context and nesting the decorators does not produce the desired outcome
@register(
    "zac:configureAdviceRequest",
    AdviceApprovalContextSerializer,
    ConfigureReviewRequestSerializer,
)
def get_context(task: Task) -> AdviceApprovalContext:
    context = get_advice_approval_context(task)
    context["review_type"] = KownslTypes.advice
    return AdviceApprovalContext(**context)


@register(
    "zac:configureApprovalRequest",
    AdviceApprovalContextSerializer,
    ConfigureReviewRequestSerializer,
)
def get_context(task: Task) -> AdviceApprovalContext:
    context = get_advice_approval_context(task)
    context["review_type"] = KownslTypes.approval
    return AdviceApprovalContext(**context)
