from typing import List

from django.contrib.auth import get_user_model

from django_camunda.camunda_models import factory
from django_camunda.client import get_client

from zac.camunda.data import ProcessInstance, Task
from zac.camunda.forms import extract_task_form

from .forms import (
    ConfigureAdviceRequestForm,
    ConfigureApprovalRequestForm,
    SelectDocumentsForm,
    SelectUsersForm,
)

User = get_user_model()


FORM_KEYS = {
    "zac:documentSelectie": {"form": SelectDocumentsForm},
    "zac:gebruikerSelectie": {"form": SelectUsersForm},
    "zac:configureAdviceRequest": {"form": ConfigureAdviceRequestForm},
    "zac:configureApprovalRequest": {"form": ConfigureApprovalRequestForm},
}


def _resolve_assignee(username: str) -> User:
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        user = User.objects.create_user(username=username)
    return user


def get_tasks(query: dict) -> List[Task]:
    client = get_client()
    tasks = client.get("task", query)
    tasks = factory(Task, tasks)

    for task in tasks:
        if task.assignee:
            task.assignee = _resolve_assignee(task.assignee)

        task.form = extract_task_form(task, FORM_KEYS)
    return tasks


def get_zaak_tasks(zaak_url: str) -> List[Task]:
    query = {"processVariables": f"zaakUrl_eq_{zaak_url}"}
    return get_tasks(query)


def get_process_tasks(process: ProcessInstance) -> List[Task]:
    query = {"processInstanceId": process.id}
    return get_tasks(query)
