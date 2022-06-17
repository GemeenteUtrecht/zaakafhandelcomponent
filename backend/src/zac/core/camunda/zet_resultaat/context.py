from typing import List, Optional

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Prefetch

from zac.activities.constants import ActivityStatuses
from zac.activities.models import Activity
from zac.camunda.data import Task
from zac.camunda.processes import get_top_level_process_instances
from zac.camunda.user_tasks import register
from zac.checklists.models import Checklist, ChecklistQuestion, ChecklistType
from zac.contrib.kownsl.api import get_review_requests
from zac.core.camunda.utils import get_process_zaak_url
from zac.core.services import fetch_zaaktype, get_resultaattypen, get_zaak
from zgw.models.zrc import Zaak

from .serializers import (
    ZetResultaatContext,
    ZetResultaatContextSerializer,
    ZetResultaatTaskSerializer,
)


def get_unanswered_checklist_questions_for_zaak(
    zaak: Zaak,
) -> List[ChecklistQuestion]:
    checklist = Checklist.objects.filter(zaak=zaak.url).prefetch_related(
        "checklistanswer_set"
    )
    if checklist.exists():
        checklist = checklist.get()
        answered_questions = [
            answer.question for answer in checklist.checklistanswer_set.all()
        ]
    else:
        answered_questions = []

    zaaktype_url = zaak.zaaktype if type(zaak.zaaktype) == str else zaak.zaaktype.url
    checklist_type = ChecklistType.objects.filter(
        zaaktype=zaaktype_url
    ).prefetch_related(
        Prefetch(
            "checklistquestion_set",
            queryset=(
                ChecklistQuestion.objects.prefetch_related("questionchoice_set").all()
            ),
        )
    )
    if checklist_type.exists():
        checklist_type = checklist_type.get()
        return [
            question
            for question in checklist_type.checklistquestion_set.all()
            if question.question not in answered_questions
        ]

    return []


@register(
    "zac:zetResultaat",
    ZetResultaatContextSerializer,
    ZetResultaatTaskSerializer,
)
def get_context(task: Task) -> ZetResultaatContext:
    zaak_url = get_process_zaak_url(task)
    activities = (
        Activity.objects.prefetch_related("events").filter(
            zaak=zaak_url, status=ActivityStatuses.on_going
        )
        or None
    )
    zaak = get_zaak(zaak_url=zaak_url)
    checklist_questions = get_unanswered_checklist_questions_for_zaak(zaak) or None
    process_instances = get_top_level_process_instances(zaak_url)
    tasks = [task for pi in process_instances for task in pi.tasks] or None
    review_requests = [
        rr for rr in get_review_requests(zaak) if rr.completed < rr.num_assigned_users
    ] or None
    zaaktype = fetch_zaaktype(zaak.zaaktype)
    result_types = get_resultaattypen(zaaktype)
    return ZetResultaatContext(
        activities=activities,
        checklist_questions=checklist_questions,
        tasks=tasks,
        review_requests=review_requests,
        result_types=result_types,
    )
