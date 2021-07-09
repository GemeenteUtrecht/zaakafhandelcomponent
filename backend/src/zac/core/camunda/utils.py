import warnings
from typing import List, Optional

from django.contrib.auth import get_user_model

import requests
from django_camunda.camunda_models import factory
from django_camunda.client import get_client

from zac.camunda.data import ProcessInstance, Task
from zac.camunda.forms import extract_task_form

User = get_user_model()

# FIXME: cleanup
FORM_KEYS = {
    "zac:documentSelectie": True,
    "zac:gebruikerSelectie": True,
    "zac:configureAdviceRequest": True,
    "zac:configureApprovalRequest": True,
}


def _resolve_assignee(username: str) -> User:
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        user = User.objects.create_user(username=username)
    return user


def get_process_tasks(process: ProcessInstance) -> List[Task]:
    client = get_client()
    tasks = client.get("task", {"processInstanceId": process.id})
    tasks = factory(Task, tasks)

    for task in tasks:
        if task.assignee:
            task.assignee = _resolve_assignee(task.assignee)

        task.form = extract_task_form(task, FORM_KEYS)
    return tasks


def get_task(*args, **kwargs) -> Optional[Task]:
    from zac.camunda.user_tasks import get_task

    warnings.warn(
        "'zac.core.camunda.get_task' is deprecated, use 'zac.camunda.user_tasks.get_task' instead",
        DeprecationWarning,
    )
    return get_task(*args, **kwargs)


def get_process_zaak_url(process: ProcessInstance) -> str:
    camunda_client = get_client()

    try:
        return process.get_variable("zaakUrl")
    except requests.RequestException as exc:
        if exc.response.status_code != 404:
            raise

    # search parent processes
    parent_processes_response = camunda_client.get(
        "process-instance", {"subProcessInstance": process.id}
    )
    if not parent_processes_response:
        raise RuntimeError(
            "None of the (parent) processes had a zaakUrl process variable!"
        )

    parent_process = factory(ProcessInstance, parent_processes_response[0])
    return get_process_zaak_url(parent_process)
