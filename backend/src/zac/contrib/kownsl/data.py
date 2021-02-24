import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List

from django.utils.translation import gettext_lazy as _

from djchoices import ChoiceItem, DjangoChoices
from zgw_consumers.api_models.base import Model

from zac.accounts.models import User


class KownslTypes(DjangoChoices):
    advice = ChoiceItem("advice", _("Advies"))
    approval = ChoiceItem("approval", _("Accordering"))


@dataclass
class ReviewRequest(Model):
    id: uuid.UUID
    review_type: str
    num_advices: int
    num_approvals: int
    num_assigned_users: int
    created: datetime = datetime.now()
    documents: List[str] = field(default_factory=list)
    for_zaak: str = ""
    frontend_url: str = ""
    requester: str = ""
    toelichting: str = ""
    user_deadlines: Dict = field(default_factory=dict)

    def get_review_type_display(self):
        return KownslTypes.labels[self.review_type]


@dataclass
class Author(Model):
    username: str
    first_name: str
    last_name: str

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
    document: str
    source_version: int
    advice_version: int


@dataclass
class Advice(Model):
    created: datetime
    author: Author
    advice: str
    documents: List[AdviceDocument]


@dataclass
class Approval(Model):
    created: datetime
    author: Author
    approved: bool
    toelichting: str = ""
