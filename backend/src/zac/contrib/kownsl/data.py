import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List

from django.utils.translation import gettext_lazy as _

from djchoices import ChoiceItem, DjangoChoices
from zgw_consumers.api_models.base import Model

from zac.accounts.models import Group, User
from zac.core.camunda.utils import resolve_assignee


class KownslTypes(DjangoChoices):
    advice = ChoiceItem("advice", _("Advice"))
    approval = ChoiceItem("approval", _("Approval"))


@dataclass
class OpenReview(Model):
    deadline: date
    users: List[str]
    groups: List[str]

    @property
    def _users(self) -> List[User]:
        return [resolve_assignee(user) for user in self.users]

    @property
    def _groups(self) -> List[Group]:
        return [resolve_assignee(group) for group in self.groups]


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
    assigned_users: dict = field(default_factory=dict)
    user_deadlines: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    def get_review_type_display(self):
        return KownslTypes.labels[self.review_type]

    @property
    def completed(self) -> int:
        return self.num_advices + self.num_approvals


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
