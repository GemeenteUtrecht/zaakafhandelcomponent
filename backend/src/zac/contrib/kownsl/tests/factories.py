from dataclasses import dataclass
from datetime import datetime
from typing import List

import factory
import factory.fuzzy
from django.utils.translation import gettext_lazy as _
from djchoices import ChoiceItem, DjangoChoices
from zgw_consumers.api_models.base import Model


class KownslTypes(DjangoChoices):
    advice = ChoiceItem("advice", _("Advice"))
    approval = ChoiceItem("approval", _("Approval"))


@dataclass
class ZaakDocument(Model):
    download_url: str
    name: str
    extra: str
    title: str


class ZaakDocumentFactory(factory.Factory):
    download_url = factory.Faker("url")
    name = factory.Faker("file_name", category="text", extension="docx")
    extra = factory.fuzzy.FuzzyChoice(["openbaar", "intern", "zeer geheim"])
    title = factory.fuzzy.FuzzyChoice(["v100", "v110", "v200"])

    class Meta:
        model = ZaakDocument


@dataclass
class ReviewRequest(Model):
    created: datetime
    documents: List[str]
    review_type: str
    toelichting: str


class ReviewRequestFactory(factory.Factory):
    created = factory.Faker("date")
    documents = factory.List([factory.Faker("url") for i in range(2)])
    review_type = factory.fuzzy.FuzzyChoice(KownslTypes.values)
    toelichting = factory.Faker("text")

    class Meta:
        model = ReviewRequest


@dataclass
class Advice(Model):
    created: datetime
    author: str
    advice: str
    documents: List[str]


@dataclass
class Approval(Model):
    created: datetime
    author: str
    approved: bool
    toelichting: str


class ApprovalFactory(factory.Factory):
    created = factory.Faker("date")
    author = factory.Faker("name")
    approved = factory.Faker("pybool")
    toelichting = factory.Faker("text")

    class Meta:
        model = Approval


class AdviceFactory(factory.Factory):
    created = factory.Faker("date")
    author = factory.Faker("name")
    advice = factory.Faker("text")
    documents = factory.List([factory.Faker("url") for i in range(2)])

    class Meta:
        model = Advice
