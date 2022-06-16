from django.db.models import Prefetch

from zac.activities.constants import ActivityStatuses
from zac.activities.models import Activity
from zac.camunda.data import Task
from zac.camunda.processes import get_top_level_process_instances
from zac.camunda.user_tasks import register
from zac.checklists.models import Checklist, ChecklistQuestion
from zac.contrib.kownsl.api import get_review_requests
from zac.core.camunda.utils import get_process_zaak_url
from zac.core.services import fetch_zaaktype, get_resultaattypen, get_zaak

from .serializers import (
    ResultaatZettenContext,
    ResultaatZettenContextSerializer,
    ResultaatZettenTaskSerializer,
)


@register(
    "zac:resultaatZetten",
    ResultaatZettenContextSerializer,
    ResultaatZettenTaskSerializer,
)
def get_context(task: Task) -> ResultaatZettenContext:
    zaak_url = get_process_zaak_url(task, zaak_url_variable="hoofdZaakUrl")
    activities = Activity.objects.prefetch_related("events_set").filter(
        zaak=zaak_url, status=ActivityStatuses.on_going
    )
    checklist = (
        Checklist.objects.select_related("checklist_type")
        .select_related("checklist_type")
        .prefetch_related(
            Prefetch(
                "checklistquestion_set",
                queryset=(
                    ChecklistQuestion.objects.prefetch_related(
                        "questionchoice_set"
                    ).all()
                ),
            )
        )
        .filter(zaak=zaak_url)
    )
    checklist_questions = [
        question for question in checklist.checklisttype.checklistquestion_set.all()
    ]
    process_instances = get_top_level_process_instances(zaak_url)
    tasks = [task for pi in process_instances for task in pi.tasks]
    zaak = get_zaak(zaak_url=zaak_url)
    review_requests = [
        rr for rr in get_review_requests(zaak) if rr.completed < rr.num_assigned_users
    ]
    zaaktype = fetch_zaaktype(zaak.zaaktype)
    result_types = get_resultaattypen(zaaktype)
    return ResultaatZettenContext(
        activities=activities,
        checklist_questions=checklist_questions,
        tasks=tasks,
        review_requests=review_requests,
        result_types=result_types,
    )
