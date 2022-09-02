from typing import List

from django.db.models import Prefetch

from zac.activities.constants import ActivityStatuses
from zac.activities.models import Activity
from zac.camunda.data import Task
from zac.camunda.processes import get_top_level_process_instances
from zac.camunda.user_tasks import register
from zac.contrib.kownsl.api import get_review_requests
from zac.core.camunda.utils import get_process_zaak_url
from zac.core.services import fetch_zaaktype, get_resultaattypen, get_zaak, get_zaaktype
from zac.objects.checklists.data import Checklist, ChecklistQuestion, ChecklistType
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

    zaaktype = (
        get_zaaktype(zaak.zaaktype) if isinstance(zaak.zaaktype, str) else zaak.zaaktype
    )
    checklisttype = ChecklistType.objects.filter(
        zaaktype_catalogus=zaaktype.catalogus,
        zaaktype_identificatie=zaaktype.identificatie,
    ).prefetch_related(
        Prefetch(
            "checklistquestion_set",
            queryset=(
                ChecklistQuestion.objects.prefetch_related("questionchoice_set").all()
            ),
        )
    )
    if checklisttype.exists():
        checklisttype = checklisttype.get()
        return [
            question
            for question in checklisttype.checklistquestion_set.all()
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

    all_result_types = get_resultaattypen(zaaktype)
    chosen_result_types = []
    if result_type_choices := task.get_variable("resultaatTypeKeuzes", default=None):
        for result in all_result_types:
            if result.omschrijving in result_type_choices:
                chosen_result_types.append(result)

    return ZetResultaatContext(
        activities=activities,
        checklist_questions=checklist_questions,
        tasks=tasks,
        review_requests=review_requests,
        result_types=chosen_result_types or all_result_types,
    )
