from dataclasses import dataclass
from typing import List

from django_camunda.camunda_models import Task

from zac.accounts.models import AccessRequest
from zac.activities.models import Activity
from zac.contrib.objects.checklists.data import ChecklistAnswer
from zgw.models import Zaak


@dataclass
class ActivityGroup:
    activities: List[Activity]
    zaak: Zaak
    zaak_url: str


@dataclass
class AccessRequestGroup:
    access_requests: List[AccessRequest]
    zaak: Zaak
    zaak_url: str


@dataclass
class TaskAndCase:
    task: Task
    zaak: Zaak


@dataclass
class ChecklistAnswerGroup:
    checklist_answers: List[ChecklistAnswer]
    zaak: Zaak
    zaak_url: str
