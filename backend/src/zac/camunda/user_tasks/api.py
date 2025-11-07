from typing import Dict, List, Optional

from django.conf import settings
from django.utils.translation import gettext_lazy as _

from django_camunda.api import complete_task, get_task as _get_task
from django_camunda.camunda_models import factory
from django_camunda.client import get_client, get_client as get_camunda_client
from django_camunda.types import CamundaId
from rest_framework.exceptions import ValidationError

from zac.accounts.models import User
from zac.camunda.client import CAMUNDA_CLIENT_CLASS
from zac.camunda.constants import AssigneeTypeChoices
from zac.camunda.data import Task
from zac.camunda.forms import extract_task_form
from zac.camunda.models import KillableTask
from zac.camunda.variable_instances import get_camunda_variable_instances
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


def set_assignee(task_id: str, assignee: str):
    camunda_client = get_client()
    camunda_client.post(
        f"task/{task_id}/assignee",
        json={"userId": assignee},
    )


def set_assignee_and_complete_task(
    task: Task, user_assignee: User, variables: dict = dict
):
    # First make sure the task has the right assignee for historical purposes
    if (
        not task.assignee
        or task.assignee != user_assignee
        or task.assignee_type == AssigneeTypeChoices.group
    ):
        set_assignee(task.id, user_assignee)

    # Then complete the task.
    complete_task(
        task.id,
        variables=variables,
    )


def get_camunda_user_task_count(
    assignees: List[str], client: Optional[CAMUNDA_CLIENT_CLASS] = None
) -> int:
    if not assignees:
        return 0

    if not client:
        client = get_client()

    response = client.post("task/count", json={"assigneeIn": assignees})
    return response["count"]


def get_camunda_user_tasks(
    payload: Dict,
    client: Optional[CAMUNDA_CLIENT_CLASS] = None,
) -> List[Task]:
    if not client:
        client = get_client()

    tasks = client.post("task", json=payload)
    if not tasks:
        return []

    tasks = factory(Task, tasks)

    # Group assignees in dictionary for performance
    assignees = list({task.assignee for task in tasks})
    assignees = {
        assignee: resolve_assignee(assignee) for assignee in assignees if assignee
    }

    # Resolve assignees from dictionary
    for task in tasks:
        task.assignee = assignees.get(task.assignee)
        task.form = extract_task_form(task, FORM_KEYS)

    return tasks


def get_camunda_user_tasks_for_zaak(
    zaak_url: str, exclude_zaak_creation: bool
) -> List[Task]:
    payload = {
        "processVariables": [{"name": "zaakUrl", "operator": "eq", "value": zaak_url}]
    }
    if exclude_zaak_creation:
        payload["processDefinitionKeyNotIn"] = (
            settings.CREATE_ZAAK_PROCESS_DEFINITION_KEY
        )
    return get_camunda_user_tasks(payload=payload)


def get_camunda_user_tasks_for_user_groups(
    user: User, client: Optional[CAMUNDA_CLIENT_CLASS] = None
) -> List[Task]:
    groups = list(user.groups.all().values_list("name", flat=True))
    return get_camunda_user_tasks_for_assignee(
        [f"{AssigneeTypeChoices.group}:{group}" for group in groups],
        client=client,
    )


def get_camunda_user_tasks_for_assignee(
    assignees: List[str], client: Optional[CAMUNDA_CLIENT_CLASS] = None
) -> List[Task]:
    if not assignees:
        return []

    return get_camunda_user_tasks({"assigneeIn": assignees}, client=client)


def get_zaak_urls_from_tasks(
    tasks: List[Task], client: Optional[CAMUNDA_CLIENT_CLASS] = None
) -> Optional[Dict[str, str]]:
    if not tasks:
        return None

    if not client:
        client = get_client()

    pids_and_tasks = {str(task.process_instance_id): task for task in tasks}
    pids = list(pids_and_tasks.keys())
    if not pids:
        return None

    variables = get_camunda_variable_instances(
        {"processInstanceIdIn": pids, "variableName": "zaakUrl"}, client=client
    )
    pids_and_urls = {
        variable["process_instance_id"]: variable["value"] for variable in variables
    }
    return {
        pids_and_tasks[process_instance_id].id: url
        for process_instance_id, url in pids_and_urls.items()
        if url and process_instance_id in pids_and_tasks
    }
