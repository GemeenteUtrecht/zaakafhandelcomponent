from dataclasses import dataclass
from typing import List, Optional

from django.utils.translation import gettext_lazy as _

from zgw_consumers.api_models.base import Model

from zac.accounts.models import User

from .models import ChecklistLock


@dataclass
class ChecklistAnswer(Model):
    question: str
    answer: str
    remarks: Optional[str] = ""
    document: Optional[str] = ""
    user_assignee: Optional[str] = None
    group_assignee: Optional[str] = None


@dataclass
class Checklist(Model):
    answers: List[ChecklistAnswer]
    locked: bool
    zaak: str

    def get_locked_by(self) -> Optional[User]:
        qs = ChecklistLock.objects.filter(url=self.zaak)
        if qs.exists():
            return ChecklistLock.user
        return None


@dataclass
class QuestionChoice(Model):
    name: str
    value: str


@dataclass
class ChecklistQuestion(Model):
    question: str
    choices: List[QuestionChoice]
    order: int

    @property
    def valid_choice_values(self) -> Optional[List[str]]:
        if valid_choices := [choice.value for choice in self.choices]:
            return valid_choices
        return None


@dataclass
class ChecklistType(Model):
    zaaktype_catalogus: str
    zaaktype_identificaties: List[str]
    questions: List[ChecklistQuestion]
