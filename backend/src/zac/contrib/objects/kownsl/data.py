import uuid
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional, Union
from uuid import UUID

from django.conf import settings
from django.utils.translation import gettext_lazy as _

from djchoices import ChoiceItem, DjangoChoices
from furl import furl
from zgw_consumers.api_models.base import Model, factory
from zgw_consumers.api_models.documenten import Document

from zac.camunda.constants import AssigneeTypeChoices
from zac.camunda.user_tasks import Context
from zac.core.utils import build_absolute_url
from zac.elasticsearch.documents import InformatieObjectDocument
from zac.elasticsearch.searches import search_informatieobjects
from zgw.models.zrc import Zaak


class KownslTypes(DjangoChoices):
    advice = ChoiceItem("advice", _("Advice"))
    approval = ChoiceItem("approval", _("Approval"))


@dataclass
class OpenReview(Model):
    deadline: date
    users: List[str]
    groups: List[str]


@dataclass
class AdviceDocument(Model):
    advice_version: int
    source_version: int
    document: str


@dataclass
class Advice(Model):
    created: datetime
    advice: str
    advice_documents: List[AdviceDocument]
    author: dict = field(default_factory=dict)
    group: dict = field(default_factory=dict)

    # for internal use only
    documents: list = field(default_factory=list)


@dataclass
class Approval(Model):
    created: datetime
    approved: bool
    author: dict = field(default_factory=dict)
    group: dict = field(default_factory=dict)
    toelichting: str = ""


@dataclass
class AssignedUsers(Model):
    email_notification: bool = False
    deadline: date

    user_assignees: list = field(default_factory=list)
    group_assignees: list = field(default_factory=list)

    @property
    def deadline(self) -> date:
        return self._deadline

    @deadline.setter
    def deadline(self, deadline: Union[date, str]):
        self._deadline = (
            date.fromisoformat(deadline) if type(deadline) == str else deadline
        )


@dataclass
class Reviews(Model):
    id: uuid.UUID
    review_type: str
    review_request: str
    zaak: str

    reviews: list = field(default_factory=list)

    @property
    def reviews(self) -> List[Union[Advice, Approval]]:
        return self._reviews

    @reviews.setter
    def reviews(self, reviews: List[Dict]):
        if self.review_type == KownslTypes.advice:
            self._reviews = factory(Advice, reviews)
        else:
            self._reviews = factory(Approval, reviews)


@dataclass
class ReviewRequest(Model):
    id: uuid.UUID
    review_type: str
    created: datetime
    documents: List[str]
    is_being_reconfigured: bool
    locked: bool
    lock_reason: str
    num_reviews_given_before_change: int
    toelichting: str
    zaak: str

    assigned_users: List[AssignedUsers] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    num_assigned_users: int = 0
    requester: dict = field(default_factory=dict)
    user_deadlines: dict = field(default_factory=dict)

    # for internal use only
    zaak_documents: list = field(default_factory=list)
    fetched_zaak_documents: bool = False
    reviews: list = field(default_factory=list)
    fetched_reviews: bool = False
    open_reviews: list = field(default_factory=list)

    @property
    def num_assigned_users(self) -> int:
        return self._num_assigned_users

    @num_assigned_users.setter
    def num_assigned_users(self, obj):
        self._num_assigned_users = self.num_reviews_given_before_change + sum(
            [
                len(assignees["user_assignees"] or [])
                + len(assignees["group_assignees"] or [])
                for assignees in self.assigned_users
            ]
        )

    def get_completed(self) -> int:
        return len(self.get_reviews())

    def _resolve_advice_documents_for_advices(
        self, advices: List[Advice]
    ) -> List[Advice]:
        documents = set(
            advice_document.document
            for advice in advices
            for advice_document in advice.advice_documents
        )
        if documents:
            _documents = search_informatieobjects(urls=list(documents))
            documents = {doc.url: doc for doc in _documents}
            for advice in advices:
                advice_documents = []
                for advice_document in advice.advice_documents:
                    advice_document.document = documents[advice_document.document]
                    advice_documents.append(advice_document)

                advice.documents = advice_documents

        return advices

    def get_reviews(self) -> List[Union[Advice, Approval]]:
        if not self.fetched_reviews:
            from zac.contrib.objects.services import get_reviews_for_review_request

            if reviews := get_reviews_for_review_request(self):
                self.reviews = reviews.reviews
                if self.review_type == KownslTypes.advice:
                    self.reviews = self._resolve_advice_documents_for_advices(
                        self.reviews
                    )
            self.fetched_reviews = True
        return self.reviews

    def get_open_reviews(self) -> List[OpenReview]:
        if not getattr(self, "open_reviews", []):
            user_deadlines = deepcopy(self.user_deadlines)

            for review in self.get_reviews():
                if name := review.group.get("name"):
                    user_deadlines.pop(f"{AssigneeTypeChoices.group}:{name}", None)

                author = f"{AssigneeTypeChoices.user}:{review.author['username']}"
                user_deadlines.pop(author, None)

            # create dictionary of users for their information
            assignees = {}
            for assignee in self.assigned_users:
                for user in assignee.user_assignees:
                    assignees[f"{AssigneeTypeChoices.user}:{user['username']}"] = user[
                        "full_name"
                    ]
                for group in assignee.group_assignees:
                    assignees[f"{AssigneeTypeChoices.group}:{group['name']}"] = group[
                        "full_name"
                    ]

            # we want a dictionary of deadlines with the users and groups that still
            # need to review.
            deadline_users = {
                deadline: {"deadline": deadline, "users": [], "groups": []}
                for deadline in user_deadlines.values()
            }
            for user_or_group, deadline in user_deadlines.items():
                assignee = assignees[user_or_group]
                if AssigneeTypeChoices.group in user_or_group:
                    deadline_users[deadline]["groups"].append(assignee)
                else:
                    deadline_users[deadline]["users"].append(assignee)

            # sort for sake of sorting
            open_reviews = sorted(
                list(deadline_users.values()), key=lambda x: x["deadline"]
            )
            for open_review in open_reviews:
                open_review["users"] = sorted(open_review["users"])
                open_review["groups"] = sorted(open_review["groups"])

            self.open_reviews = factory(OpenReview, open_reviews)
        return self.open_reviews

    def get_frontend_url(self) -> str:
        if not hasattr(self, "_frontend_url"):
            url = furl(settings.UI_ROOT_URL)
            url.path.segments += [
                "kownsl",
                "review-request",
                self.review_type,
            ]
            self._frontend_url = build_absolute_url(
                url.url,
                params={"uuid": self.id},
            )
        return self._frontend_url

    def get_review_type_display(self):
        return KownslTypes.labels[self.review_type]

    def get_zaak_documents(self) -> List[Optional[InformatieObjectDocument]]:
        if not self.fetched_zaak_documents:
            self.fetched_zaak_documents = True
            self.zaak_documents = (
                search_informatieobjects(urls=self.documents) if self.documents else []
            )

        return self.zaak_documents


@dataclass
class AdviceApprovalContext(Context):
    camunda_assigned_users: AssignedUsers
    documents_link: str
    review_type: str
    title: str
    zaak_informatie: Zaak

    documents: Optional[List[InformatieObjectDocument]] = None
    id: Optional[UUID] = None
    previously_selected_documents: list = field(default_factory=list)
    previously_assigned_users: list = field(default_factory=list)
    update: bool = False
