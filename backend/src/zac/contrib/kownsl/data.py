import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional, Union
from uuid import UUID

from django.utils.translation import gettext_lazy as _

from djchoices import ChoiceItem, DjangoChoices
from zgw_consumers.api_models.base import Model
from zgw_consumers.api_models.documenten import Document

from zac.accounts.models import Group, User
from zac.camunda.constants import AssigneeTypeChoices
from zac.camunda.user_tasks import Context
from zac.core.camunda.utils import resolve_assignee
from zgw.models.zrc import Zaak


class KownslTypes(DjangoChoices):
    advice = ChoiceItem("advice", _("Advice"))
    approval = ChoiceItem("approval", _("Approval"))


@dataclass
class OpenReview(Model):
    deadline: date
    users: List[str]
    groups: List[str]

    @property
    def users(self) -> List[User]:
        return self._users

    @users.setter
    def users(self, users: Union[User, str]):
        self._users = [
            resolve_assignee(user) if type(user) == str else user for user in users
        ]

    @property
    def groups(self) -> List[User]:
        return self._groups

    @groups.setter
    def groups(self, groups: Union[Group, str]):
        self._groups = [
            resolve_assignee(
                group
                if AssigneeTypeChoices.group in group
                else f"{AssigneeTypeChoices.group}:{group}"
            )
            if type(group) == str
            else group
            for group in groups
        ]


@dataclass
class Author(Model):
    username: str
    first_name: str
    last_name: str
    full_name: str

    @property
    def user(self):
        if not hasattr(self, "_user"):
            self._user, _ = User.objects.get_or_create(
                username=self.username,
                defaults={
                    "first_name": self.first_name,
                    "last_name": self.last_name,
                },
            )
        return self._user

    def get_full_name(self):
        return self.user.get_full_name()


@dataclass
class AdviceDocument(Model):
    advice_version: int
    source_version: int
    document: str


@dataclass
class Advice(Model):
    created: datetime
    author: Author
    advice: str
    documents: List[AdviceDocument]
    group: str = ""


@dataclass
class Approval(Model):
    created: datetime
    author: Author
    approved: bool
    group: str = ""
    toelichting: str = ""


@dataclass
class AssignedUsers(Model):
    deadline: date
    user_assignees: List[str]
    group_assignees: List[str]
    email_notification: bool = False

    @property
    def user_assignees(self) -> List[User]:
        return self._user_assignees

    @user_assignees.setter
    def user_assignees(self, user_assignees: Union[User, str]):
        self._user_assignees = [
            resolve_assignee(user) if type(user) == str else user
            for user in user_assignees
        ]

    @property
    def group_assignees(self) -> List[User]:
        return self._group_assignees

    @group_assignees.setter
    def group_assignees(self, group_assignees: Union[Group, str]):
        self._group_assignees = [
            resolve_assignee(
                group
                if AssigneeTypeChoices.group in group
                else f"{AssigneeTypeChoices.group}:{group}"
            )
            if type(group) == str
            else group
            for group in group_assignees
        ]

    @property
    def deadline(self) -> date:
        return self._deadline

    @deadline.setter
    def deadline(self, deadline: Union[date, str]):
        self._deadline = (
            date.fromisoformat(deadline) if type(deadline) == str else deadline
        )


@dataclass
class ConfigureReviewRequest:
    assigned_users: List[AssignedUsers]
    selected_documents: Optional[List[str]] = field(default_factory=list)
    toelichting: Optional[str] = ""
    id: Optional[str] = None


@dataclass
class AdviceApprovalContext(Context):
    title: str
    zaak_informatie: Zaak
    documents: List[Document]
    review_type: str
    camunda_assigned_users: AssignedUsers
    id: Optional[UUID] = None
    previously_selected_documents: list = field(default_factory=list)
    previously_assigned_users: list = field(default_factory=list)
    update: bool = False


@dataclass
class ReviewRequest(Model):
    id: uuid.UUID
    num_advices: int
    num_approvals: int
    num_assigned_users: int
    review_type: str
    created: datetime = datetime.now()
    documents: List[str] = field(default_factory=list)
    for_zaak: str = ""
    frontend_url: str = ""
    locked: bool = False
    lock_reason: str = ""
    open_reviews: List[OpenReview] = field(default_factory=list)
    requester: Dict = field(default_factory=dict)
    toelichting: str = ""
    assigned_users: List[AssignedUsers] = field(default_factory=list)
    user_deadlines: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    def get_review_type_display(self):
        return KownslTypes.labels[self.review_type]

    @property
    def completed(self) -> int:
        return self.num_advices + self.num_approvals
