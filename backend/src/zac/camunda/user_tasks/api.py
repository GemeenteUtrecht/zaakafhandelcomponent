from typing import List, Optional

from django.http import Http404
from django.utils.translation import gettext_lazy as _

from django_camunda.api import get_task as _get_task
from django_camunda.client import get_client as get_camunda_client
from django_camunda.types import CamundaId
from rest_framework.exceptions import ValidationError

from zac.camunda.data import Task
from zac.camunda.forms import extract_task_form
from zac.camunda.models import KillableTask
from zac.core.camunda.utils import FORM_KEYS, resolve_assignee


def get_task(task_id: CamundaId, check_history=False) -> Optional[Task]:
    task = _get_task(task_id, check_history=check_history, factory_cls=Task)

    # check if task is not None
    # add Django integration
    if task is not None:
        if task.assignee:
            task.assignee = resolve_assignee(task.assignee)
        task.form = extract_task_form(task, FORM_KEYS)

    return task


def get_killable_camunda_tasks() -> List[str]:
    return KillableTask.objects.all().values_list("name", flat=True)


def get_killability_of_task(task_name: str) -> bool:
    killable_tasks = get_killable_camunda_tasks()
    return task_name in killable_tasks


def get_task_activity_instance_id(task_id: CamundaId) -> str:
    from zac.camunda.user_tasks.history import get_task_history

    # The task history endpoint exposes the required information.
    # The task endpoint itself does not have this information.
    task_history = get_task_history({"taskId": task_id})
    task_history = [task for k, task in task_history.items()]
    return str(task_history[0]["activity_instance_id"])


def cancel_activity_instance_of_task(task: Task):
    killable = get_killability_of_task(task.name)
    if not killable:
        raise ValidationError(_("This task can not be canceled."))

    activity_instance_id = get_task_activity_instance_id(str(task.id))
    client = get_camunda_client()
    data = {
        "skipIoMappings": "true",
        "instructions": [
            {"type": "cancel", "activityInstanceId": str(activity_instance_id)}
        ],
    }
    # A raise_for_status check is done within the client.
    client.post(
        f"process-instance/{str(task.process_instance_id)}/modification", json=data
    )
