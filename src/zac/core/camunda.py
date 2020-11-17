from typing import List, Optional

from django.contrib.auth import get_user_model

import requests
from django_camunda.client import get_client
from django_camunda.types import CamundaId
from zgw_consumers.api_models.base import (  # django_camunda can't handle inheritance yet
    factory,
)

from zac.camunda.data import ProcessInstance, Task
from zac.camunda.forms import extract_task_form

from .forms import (
    ConfigureAdviceRequestForm,
    ConfigureApprovalRequestForm,
    SelectDocumentsForm,
    SelectUsersForm,
    UsersReviewRequestFormSet,
)

User = get_user_model()


FORM_KEYS = {
    "zac:documentSelectie": {"form": SelectDocumentsForm},
    "zac:gebruikerSelectie": {"form": SelectUsersForm},
    "zac:configureAdviceRequest": {
        "form": ConfigureAdviceRequestForm,
        "formset": UsersReviewRequestFormSet,
    },
    "zac:configureApprovalRequest": {
        "form": ConfigureApprovalRequestForm,
        "formset": UsersReviewRequestFormSet,
    },
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


def get_task(task_id: CamundaId) -> Optional[Task]:
    client = get_client()
    try:
        data = client.get(f"task/{task_id}")
    except requests.HTTPError as exc:
        if exc.response.status_code == 404:
            # see if we can get it from the history
            historical = client.get("history/task", {"taskId": task_id})
            if not historical:
                return None

            assert (
                len(historical) < 2
            ), f"Found multiple tasks in the history for ID {task_id}"

            data = historical[0]
            # these properties do not exist in the history API:
            # https://docs.camunda.org/manual/7.11/reference/rest/history/task/get-task-query/
            data.update(
                {
                    "created": data["start_time"],
                    "delegation_state": None,
                    "suspended": False,
                    "form_key": None,  # cannot determine this...
                    "historical": True,
                }
            )

        else:
            raise

    task = factory(Task, data)

    # add Django integration
    if task.assignee:
        task.assignee = _resolve_assignee(task.assignee)
    task.form = extract_task_form(task, FORM_KEYS)

    return task


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
