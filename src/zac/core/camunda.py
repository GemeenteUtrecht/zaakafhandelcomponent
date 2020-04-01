from typing import List

from django.contrib.auth import get_user_model

from django_camunda.camunda_models import Task, factory
from django_camunda.client import get_client

User = get_user_model()


def _resolve_assignee(username: str) -> User:
    user = User.objects.get(username=username)
    return user


def get_zaak_tasks(zaak_url: str) -> List[Task]:
    client = get_client()
    tasks = client.get("task", {"processVariables": f"zaakUrl_eq_{zaak_url}"},)
    tasks = factory(Task, tasks)
    for task in tasks:
        if task.assignee:
            task.assignee = _resolve_assignee(task.assignee)
    return tasks


def complete_task(task_id: str, variables: dict) -> None:
    client = get_client()
    client.post(f"task/{task_id}/complete", json={"variables": variables})
