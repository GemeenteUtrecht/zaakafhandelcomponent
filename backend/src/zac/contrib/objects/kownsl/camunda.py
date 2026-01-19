from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Union

from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from zgw_consumers.api_models.zaken import ZaakEigenschap

from zac.accounts.models import User
from zac.accounts.permission_loaders import add_permissions_for_advisors
from zac.api.context import get_zaak_context
from zac.camunda.constants import AssigneeTypeChoices
from zac.camunda.data import Task
from zac.camunda.user_tasks import register, usertask_context_serializer
from zac.contrib.objects.services import get_review_request
from zac.core.api.fields import SelectDocumentsCamundaField
from zac.core.camunda.utils import resolve_assignee
from zac.core.services import get_zaakeigenschappen
from zac.elasticsearch.searches import search_informatieobjects
from zac.tests.compat import APIModelSerializer
from zgw.models.zrc import Zaak

from ..serializers import (
    MetaObjectGroupSerializerSlugRelatedField,
    MetaObjectUserSerializer,
    MetaObjectUserSerializerSlugRelatedField,
)
from ..services import create_review_request, update_review_request
from .cache import invalidate_review_requests_cache
from .constants import FORM_KEY_REVIEW_TYPE_MAPPING, KownslTypes
from .data import AssignedUsers, ReviewContext, ReviewRequest
from .fields import SelectZaakEigenschappenKownslField


class ZaakInformatieTaskSerializer(APIModelSerializer):
    class Meta:
        dataclass = Zaak
        fields = (
            "omschrijving",
            "toelichting",
        )


class CamundaAssignedUsersSerializer(APIModelSerializer):
    """
    Select users or groups and assign deadlines to those users in the configuration of
    review requests such as the advice and approval review requests.

    """

    user_assignees = MetaObjectUserSerializerSlugRelatedField(
        slug_field="username",
        queryset=User.objects.all(),
        # help_text=_(
        #     "Users assigned to the review request from within the camunda process."
        # ),
        many=True,
        allow_null=True,
        required=True,
    )
    group_assignees = MetaObjectGroupSerializerSlugRelatedField(
        slug_field="name",
        queryset=Group.objects.all(),
        help_text=_(
            "Groups assigned to the review request from within the camunda process."
        ),
        many=True,
        allow_null=True,
        required=True,
    )

    class Meta:
        dataclass = AssignedUsers
        fields = [
            "user_assignees",
            "group_assignees",
        ]


class AssignedUsersSerializer(CamundaAssignedUsersSerializer):
    """
    Select users or groups and assign deadlines to those users in the configuration of
    review requests such as the advice and approval review requests.

    """

    user_assignees = MetaObjectUserSerializerSlugRelatedField(
        slug_field="username",
        queryset=User.objects.all(),
        help_text=_("Users assigned to the review request from within the ZAC."),
        many=True,
        allow_null=True,
        required=True,
    )
    group_assignees = MetaObjectGroupSerializerSlugRelatedField(
        slug_field="name",
        queryset=Group.objects.all(),
        help_text=_("Groups assigned to the review request from within the ZAC."),
        many=True,
        allow_null=True,
        required=True,
    )
    email_notification = serializers.BooleanField(
        default=True,
        help_text=_("Send an email notification about the review request."),
    )
    deadline = serializers.DateField(
        input_formats=["%Y-%m-%d"],
        help_text=_("On this date the review must be submitted."),
    )

    class Meta:
        dataclass = CamundaAssignedUsersSerializer.Meta.dataclass
        fields = CamundaAssignedUsersSerializer.Meta.fields + [
            "email_notification",
            "deadline",
        ]

    def validate_user_assignees(self, user_assignees):
        if len(user_assignees) > len(set(user_assignees)):
            raise serializers.ValidationError("Assigned users need to be unique.")
        return user_assignees

    def validate_group_assignees(self, group_assignees):
        if len(group_assignees) > len(set(group_assignees)):
            raise serializers.ValidationError("Assigned groups need to be unique.")
        return group_assignees

    def validate(self, attrs):
        if not attrs["group_assignees"] and not attrs["user_assignees"]:
            raise serializers.ValidationError(
                "You need to select either a user or a group."
            )
        return attrs


class ZaakEigenschapReviewContextSerializer(APIModelSerializer):
    naam = serializers.CharField(source="eigenschap.naam")

    class Meta:
        dataclass = ZaakEigenschap
        fields = ("naam", "waarde", "url")


@usertask_context_serializer
class ReviewContextSerializer(APIModelSerializer):
    camunda_assigned_users = CamundaAssignedUsersSerializer(
        help_text=_("Users or groups assigned from within the camunda process.")
    )
    documents_link = serializers.URLField(
        help_text=_("URL-reference to paginated documents endpoint.")
    )
    previously_assigned_users = AssignedUsersSerializer(
        help_text=_("A list of previously assigned users"), many=True, required=False
    )
    review_type = serializers.ChoiceField(
        choices=KownslTypes.choices,
    )
    previously_selected_documents = serializers.ListField(
        child=serializers.URLField(required=False),
        help_text=_("A list of previously selected documents."),
        required=False,
    )
    previously_selected_zaakeigenschappen = serializers.ListField(
        child=serializers.URLField(required=False),
        help_text=_("A list of previously selected ZAAKEIGENSCHAPs."),
        required=False,
    )
    toelichting = serializers.CharField(
        help_text=_("A previously given comment regarding the review request."),
        required=False,
    )
    zaakeigenschappen = ZaakEigenschapReviewContextSerializer(many=True)
    zaak_informatie = ZaakInformatieTaskSerializer()

    class Meta:
        dataclass = ReviewContext
        fields = (
            "camunda_assigned_users",
            "documents_link",
            "id",
            "previously_assigned_users",
            "review_type",
            "previously_selected_documents",
            "previously_selected_zaakeigenschappen",
            "title",
            "toelichting",
            "zaakeigenschappen",
            "zaak_informatie",
        )


class ConfigureReviewRequestSerializer(APIModelSerializer):
    """
    This serializes configure review requests such as
    advice and approval review requests.

    Must have a ``task`` and ``request`` in its ``context``.

    """

    assigned_users = AssignedUsersSerializer(
        many=True,
        help_text=_("Users assigned to review."),
    )
    created = serializers.SerializerMethodField(
        help_text=_("Datetime review request was created.")
    )
    documents = SelectDocumentsCamundaField(
        help_text=_(
            "Supporting documents for the review request. If reconfiguring this field will be ignored."
        ),
        required=False,
        allow_empty=True,
    )
    id = serializers.UUIDField(
        allow_null=True,
        help_text=_(
            "`uuid` of review request if it already exists and is reconfigured."
        ),
        required=False,
    )
    num_reviews_given_before_change = serializers.SerializerMethodField(
        help_text=_("Number of reviews given before changing the review request.")
    )
    requester = serializers.SerializerMethodField(
        help_text=_("An object containing user information of requester.")
    )
    review_type = serializers.SerializerMethodField(
        help_text=_("Review type of review request.")
    )
    toelichting = serializers.CharField(
        allow_blank=True,
        help_text=_("Additional information related to review request."),
    )
    user_deadlines = serializers.SerializerMethodField(
        help_text=_("An object with usernames and their deadlines.")
    )
    zaak = serializers.SerializerMethodField(help_text=_("URL-reference to ZAAK."))
    zaakeigenschappen = SelectZaakEigenschappenKownslField(
        help_text=_(
            "Supporting ZAAKEIGENSCHAPs for the review request. If reconfiguring this field will be ignored."
        ),
        default=list(),
        allow_empty=True,
    )

    class Meta:
        dataclass = ReviewRequest
        fields = [
            "assigned_users",
            "created",
            "documents",
            "id",
            "num_reviews_given_before_change",
            "requester",
            "review_type",
            "toelichting",
            "user_deadlines",
            "zaak",
            "zaakeigenschappen",
        ]

    def _get_review_request(self, obj) -> Optional[ReviewRequest]:
        if not hasattr(self, "_review_request"):
            if rr_id := obj.get("id"):
                self._review_request = get_review_request(rr_id)
            else:
                self._review_request = None
        return self._review_request

    def get_created(self, obj) -> str:
        if rr := self._get_review_request(obj):
            return f"{rr.created}"

        return datetime.now().isoformat()

    def get_zaak(self, obj) -> str:
        if rr := self._get_review_request(obj):
            return rr.zaak

        return self.get_zaak_from_context().url

    def get_review_type(self, obj) -> str:
        if rr := self._get_review_request(obj):
            return rr.review_type

        return FORM_KEY_REVIEW_TYPE_MAPPING[self.context["task"].form_key]

    def get_requester(self, obj) -> Dict[str, str]:
        return MetaObjectUserSerializer(instance=self.context["request"].user).data

    def get_user_deadlines(self, obj) -> Dict[str, str]:
        return {
            assignee: str(data["deadline"])
            for data in obj["assigned_users"]
            for assignee in (
                [
                    f"{AssigneeTypeChoices.user}:{user}"
                    for user in data["user_assignees"]
                ]
            )
            + (
                [
                    f"{AssigneeTypeChoices.group}:{group}"
                    for group in data["group_assignees"]
                ]
            )
        }

    def get_num_reviews_given_before_change(self, obj) -> int:
        if rr := self._get_review_request(obj):
            return len(rr.get_reviews())
        return 0

    def get_zaak_from_context(self) -> Zaak:
        if not hasattr(self, "_zaak"):
            self._zaak = get_zaak_context(self.context["task"]).zaak
        return self._zaak

    def validate_assigned_users(self, assigned_users):
        users_list = []
        groups_list = []
        for data in assigned_users:
            if not data["user_assignees"] and not data["group_assignees"]:
                raise serializers.ValidationError(
                    _("Please select at least 1 user or group."),
                    code="empty-assignees",
                )
            if any([user in users_list for user in data["user_assignees"]]):
                raise serializers.ValidationError(
                    _(
                        "Users in a serial review request process need to be unique. Please select unique users."
                    ),
                    code="unique-users",
                )
            if any([group in groups_list for group in data["group_assignees"]]):
                raise serializers.ValidationError(
                    _(
                        "Groups in a serial review request process need to be unique. Please select unique groups."
                    ),
                    code="unique-groups",
                )
            users_list.extend(data["user_assignees"])
            groups_list.extend(data["group_assignees"])

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

    def validate(self, data):
        validated_data = super().validate(data)
        # Make sure either a document or zaakeigenschap is selected
        if not validated_data.get("documents", []) and not validated_data.get(
            "zaakeigenschappen", []
        ):
            raise serializers.ValidationError(
                _("Select either documents or ZAAKEIGENSCHAPs.")
            )

        # Make sure new assignees haven't already reviewed
        if review_request := (
            self._get_review_request(validated_data)
            if validated_data.get("id")
            else None
        ):
            already_reviewed = []

            # get group names if a reviewer reviewed for a group instead of the reviewer
            for given_review in review_request.get_reviews():
                already_reviewed.append(
                    given_review.group["name"]
                    if given_review.group and given_review.group.get("name")
                    else given_review.author["username"]
                )
            assignees = []
            for review in validated_data["assigned_users"]:
                assignees.extend(
                    [f"{user}" for user in review.get("user_assignees", [])]
                )
                assignees.extend(
                    [f"{group}" for group in review.get("group_assignees", [])]
                )
            for reviewed in already_reviewed:
                if reviewed in assignees:
                    raise serializers.ValidationError(
                        _("User or group already reviewed.")
                    )

        return validated_data

    def to_representation(self, instance):
        data = super().to_representation(instance)

        # On create or update always set is_being_reconfigured to false
        data["is_being_reconfigured"] = False

        # On create or update always return locked false, lock_reason empty and metadata empty.
        data["lock_reason"] = ""
        data["locked"] = False
        data["metadata"] = dict()

        return data

    def on_task_submission(self) -> None:
        """
        On task submission create/update the review request in the objects API.

        """
        assert self.is_valid(), "Serializer must be valid"
        if id := self.validated_data.get("id"):
            self.review_request = update_review_request(
                id, self.context["request"].user, data=self.data
            )
        else:
            # Derive review_type from task.form_key
            self.review_request = create_review_request(self.data)

        invalidate_review_requests_cache(self.review_request)
        # add permission for advisors to see the zaak-detail page
        add_permissions_for_advisors(self.review_request)

    def get_process_variables(self) -> Dict[str, Union[List, str]]:
        """
        Get the required BPMN process variables for the BPMN.

        """
        # Assert is_valid has been called so that we can access validated data.
        assert self.is_valid(), "Serializer must be valid"
        assert hasattr(
            self, "review_request"
        ), "Must call on_task_submission before getting process variables."

        kownsl_users_list = []
        email_notification_list = {}
        for data in self.data["assigned_users"]:
            users = [
                f"{AssigneeTypeChoices.user}:{user['username']}"
                for user in data["user_assignees"]
            ] + [
                f"{AssigneeTypeChoices.group}:{group['name']}"
                for group in data["group_assignees"]
            ]

            kownsl_users_list.append(users)
            for user in users:
                email_notification_list[user] = data["email_notification"]

        return {
            "kownslUsersList": kownsl_users_list,
            "kownslReviewRequestId": str(self.review_request.id),
            "kownslFrontendUrl": self.review_request.get_frontend_url(),
            "emailNotificationList": email_notification_list,
        }


def get_camunda_assigned_users(task: Task) -> Dict[str, List]:
    camunda_assigned_users = task.get_variable("assignedUsers", "")
    assigned_users = {
        "user_assignees": [],
        "group_assignees": [],
    }
    for assignee in camunda_assigned_users:
        assignee = resolve_assignee(assignee)
        if isinstance(assignee, Group):
            assigned_users["group_assignees"].append(assignee)
        else:
            assigned_users["user_assignees"].append(assignee)
    return assigned_users


def get_review_request_from_task(task: Task) -> Optional[ReviewRequest]:
    rr_id = task.get_variable("kownslReviewRequestId", "")
    if review_request := get_review_request(rr_id) if rr_id else None:
        # filter out users that have already given a review so they won't be
        # seen as editable previously assigned users.
        remove_these_users = []
        for given_review in review_request.get_reviews():
            remove_these_users.append(
                (
                    given_review.group["name"]
                    if given_review.group and given_review.group.get("name")
                    else given_review.author["username"]
                )
            )

        filtered_assigned_users = []
        for review_step in review_request.assigned_users:
            review_step.user_assignees = [
                user
                for user in review_step.user_assignees
                if user["username"] not in remove_these_users
            ]
            review_step.group_assignees = [
                group
                for group in review_step.group_assignees
                if group["name"] not in remove_these_users
            ]

            if review_step.user_assignees or review_step.group_assignees:
                filtered_assigned_users.append(review_step)

        # assign filtered users again to be filtered agains the next given review
        review_request.assigned_users = filtered_assigned_users

    return review_request


def get_review_context(task: Task) -> ReviewContext:
    rr = get_review_request_from_task(task)
    zaak_context = get_zaak_context(task, require_zaaktype=True)
    zaak = zaak_context.zaak
    zaak.zaaktype = zaak_context.zaaktype
    zaakeigenschappen = get_zaakeigenschappen(zaak)
    context = {
        "camunda_assigned_users": get_camunda_assigned_users(task),
        "documents_link": zaak_context.documents_link,
        "title": f"{zaak_context.zaaktype.omschrijving} - {zaak_context.zaaktype.versiedatum}",
        "zaak_informatie": zaak_context.zaak,
        "zaakeigenschappen": zaakeigenschappen,
    }
    if rr:
        context["id"] = rr.id
        context["documents"] = search_informatieobjects(
            zaak=zaak_context.zaak.url, urls=rr.documents, size=len(rr.documents)
        )
        context["previously_assigned_users"] = rr.assigned_users
        context["previously_selected_documents"] = rr.documents
        context["previously_selected_zaakeigenschappen"] = [
            zei.url for zei in zaakeigenschappen if zei.url in rr.zaakeigenschappen
        ]

    return context


@register(
    "zac:configureAdviceRequest",
    ReviewContextSerializer,
    ConfigureReviewRequestSerializer,
)
def get_advice_context(task: Task) -> ReviewContext:
    context = get_review_context(task)
    context["review_type"] = KownslTypes.advice
    return ReviewContext(**context)


@register(
    "zac:configureApprovalRequest",
    ReviewContextSerializer,
    ConfigureReviewRequestSerializer,
)
def get_approval_context(task: Task) -> ReviewContext:
    context = get_review_context(task)
    context["review_type"] = KownslTypes.approval
    return ReviewContext(**context)
