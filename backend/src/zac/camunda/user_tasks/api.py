from typing import Optional

from django_camunda.api import get_task as _get_task
from django_camunda.types import CamundaId

from zac.core.camunda import FORM_KEYS, _resolve_assignee, extract_task_form

from ..data import Task


def get_task(task_id: CamundaId, check_history=False) -> Optional[Task]:
    task = _get_task(task_id, check_history=check_history, factory_cls=Task)

    # check if task is not None
    # add Django integration
    if task is not None:
        if task.assignee:
            task.assignee = _resolve_assignee(task.assignee)
        task.form = extract_task_form(task, FORM_KEYS)

    return task
