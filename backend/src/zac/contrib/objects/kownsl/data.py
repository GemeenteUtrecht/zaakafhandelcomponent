import uuid
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional, Union
from uuid import UUID

from django.conf import settings
from django.utils.translation import gettext_lazy as _

from furl import furl
from zgw_consumers.api_models.base import Model, factory
from zgw_consumers.api_models.zaken import ZaakEigenschap

from zac.camunda.constants import AssigneeTypeChoices
from zac.camunda.user_tasks import Context
from zac.core.services import get_zaak, get_zaakeigenschappen
from zac.core.utils import build_absolute_url
from zac.elasticsearch.documents import InformatieObjectDocument
from zac.elasticsearch.searches import search_informatieobjects
from zgw.models.zrc import Zaak

from .constants import KownslStatus, KownslTypes


@dataclass
class OpenReview(Model):
    deadline: date
    users: List[str]
    groups: List[str]


@dataclass
class ReviewDocument(Model):
    review_version: int
    source_version: int
    document: str


@dataclass
class KownslZaakEigenschap(Model):
    url: str
    naam: str
    waarde: str


@dataclass
class Advice(Model):
    created: datetime
    advice: str
    review_documents: List[ReviewDocument]
    zaakeigenschappen: List[KownslZaakEigenschap]

    author: dict = field(default_factory=dict)
    group: dict = field(default_factory=dict)

    # for internal use only
    documents: list = field(default_factory=list)


@dataclass
class Approval(Model):
    created: datetime
    approved: bool
    review_documents: List[ReviewDocument]
    zaakeigenschappen: List[KownslZaakEigenschap]

    author: dict = field(default_factory=dict)
    group: dict = field(default_factory=dict)
    toelichting: str = ""

    # for internal use only
    documents: list = field(default_factory=list)


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

    requester: dict = field(default_factory=dict)
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
    zaakeigenschappen: List[str]

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

    def _resolve_review_documents_for_reviews(
        self, reviews: Union[List[Advice], List[Approval]]
    ) -> List[Advice]:
        documents = list(
            set(
                furl(review_document.document).remove(args=True).url
                for review in reviews
                for review_document in review.review_documents
            )
        )
        if documents:
            _documents = search_informatieobjects(urls=documents, size=len(documents))
            documents = {doc.url: doc for doc in _documents}
            for review in reviews:
                review_documents = []
                for review_document in review.review_documents:
                    review_document.document = documents[
                        furl(review_document.document).remove(args=True).url
                    ]
                    review_documents.append(review_document)

                review.documents = review_documents

        return reviews

    def get_reviews(self) -> List[Union[Advice, Approval]]:
        if not self.fetched_reviews:
            from zac.contrib.objects.services import get_reviews_for_review_request

            if reviews := get_reviews_for_review_request(self):
                self.reviews = reviews.reviews
                self.reviews = self._resolve_review_documents_for_reviews(self.reviews)
            else:
                self.reviews = []

            self.fetched_reviews = True
        return self.reviews

    def get_open_reviews(self) -> List[OpenReview]:
        if not getattr(self, "open_reviews", []):
            user_deadlines = deepcopy(self.user_deadlines)

            # remove those who have already reviewed
            for review in self.get_reviews():
                # if the reviewer is a group remove the group and...
                if review.group and (name := review.group.get("name")):
                    user_deadlines.pop(f"{AssigneeTypeChoices.group}:{name}", None)

                # ... the user if the reviewer is a user
                author = f"{AssigneeTypeChoices.user}:{review.author['username']}"
                user_deadlines.pop(author, None)

            # create dictionary of users for their information as stored on the review request object
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

    def get_zaakeigenschappen(self) -> List[ZaakEigenschap]:
        if self.zaakeigenschappen and not hasattr(self, "_zaakeigenschappen"):
            zaak = (
                self.zaak
                if isinstance(self.zaak, Zaak)
                else get_zaak(zaak_url=self.zaak)
            )
            zeis = {zei.url: zei for zei in get_zaakeigenschappen(zaak)}
            self._zaakeigenschappen = [
                zeis.get(url, None)
                for url in self.zaakeigenschappen
                if zeis.get(url, None)
            ]
        else:
            self._zaakeigenschappen = self.zaakeigenschappen
        return self._zaakeigenschappen

    def get_status(self) -> str:
        if self.get_completed() >= self.num_assigned_users:
            if self.review_type == KownslTypes.advice:
                return KownslStatus.completed
            else:
                return (
                    KownslStatus.approved
                    if all([review.approved for review in self.get_reviews()])
                    else KownslStatus.not_approved
                )
        elif self.locked:
            return KownslStatus.canceled
        return KownslStatus.pending


@dataclass
class ReviewContext(Context):
    camunda_assigned_users: AssignedUsers
    documents_link: str
    review_type: str
    title: str
    zaak_informatie: Zaak
    zaakeigenschappen: List[ZaakEigenschap]

    documents: Optional[List[InformatieObjectDocument]] = None
    id: Optional[UUID] = None
    previously_selected_documents: list = field(default_factory=list)
    previously_assigned_users: list = field(default_factory=list)
    previously_selected_zaakeigenschappen: list = field(default_factory=list)
    update: bool = False
