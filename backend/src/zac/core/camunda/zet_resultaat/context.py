from typing import List

from zac.activities.constants import ActivityStatuses
from zac.activities.models import Activity
from zac.camunda.data import Task
from zac.camunda.user_tasks import register
from zac.camunda.user_tasks.api import get_camunda_user_tasks_for_zaak
from zac.contrib.dowc.api import check_document_status
from zac.contrib.objects.checklists.data import ChecklistQuestion
from zac.contrib.objects.services import (
    fetch_checklist,
    fetch_checklisttype,
    get_all_review_requests_for_zaak,
    get_reviews_for_zaak,
)
from zac.core.camunda.utils import get_process_zaak_url
from zac.core.services import fetch_zaaktype, get_resultaattypen, get_zaak, get_zaaktype
from zgw.models.zrc import Zaak

from .serializers import (
    ZetResultaatContext,
    ZetResultaatContextSerializer,
    ZetResultaatTaskSerializer,
)


def get_unanswered_checklist_questions_for_zaak(
    zaak: Zaak,
) -> List[ChecklistQuestion]:
    checklist = fetch_checklist(zaak)
    if checklist:
        answered_questions = [
            answer.question for answer in checklist.answers if answer.answer
        ]
    else:
        answered_questions = []

    zaaktype = (
        get_zaaktype(zaak.zaaktype) if isinstance(zaak.zaaktype, str) else zaak.zaaktype
    )
    checklisttype = fetch_checklisttype(zaaktype)
    if checklisttype:
        return [
            question
            for question in checklisttype.questions
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
    tasks = (
        get_camunda_user_tasks_for_zaak(zaak_url, exclude_zaak_creation=True) or None
    )
    open_documenten = check_document_status(zaak=zaak_url)

    # Fetch open review requests
    review_requests = get_all_review_requests_for_zaak(zaak)
    reviews_given = {
        str(rev.review_request): rev.reviews for rev in get_reviews_for_zaak(zaak)
    }
    open_review_requests = []
    for rr in review_requests:
        rr.reviews = reviews_given.get(str(rr.id), [])
        rr.fetched_reviews = True
        if rr.get_completed() < rr.num_assigned_users:
            open_review_requests.append(rr)

    review_requests = open_review_requests or None
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
        open_documenten=open_documenten,
    )
