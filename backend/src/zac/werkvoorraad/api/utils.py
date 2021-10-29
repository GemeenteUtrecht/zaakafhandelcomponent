from itertools import groupby
from typing import List

from django_camunda.camunda_models import factory
from django_camunda.client import get_client
from zgw_consumers.concurrent import parallel

from zac.accounts.models import AccessRequest, User
from zac.camunda.data import Task
from zac.core.camunda.utils import resolve_assignee
from zac.core.permissions import zaken_handle_access
from zac.elasticsearch.searches import search

from .data import ActivityGroup


def get_camunda_user_tasks(user: User) -> List[Task]:
    tasks = get_camunda_tasks(f"user:{user.username}")
    if not tasks:  # Try to get tasks the old way to not create breaking changes
        tasks = get_camunda_tasks(user.username)
    return tasks


def get_camunda_group_tasks(user: User) -> List[Task]:
    groups = [f"group:{group.name}" for group in user.groups.all()]
    with parallel(
        max_workers=10
    ) as executor:  # 10 parallel requests per user may be too much for camunda if lots of users are making requests - lower this if camunda starts returning 429 errors or similar
        results = executor.map(get_camunda_tasks, groups)

    # Flatten list of lists
    tasks = [task for tasks in results for task in tasks]
    return tasks


def get_camunda_tasks(assignee: str) -> List[Task]:
    client = get_client()
    tasks = client.get("task", {"assignee": assignee})

    tasks = factory(Task, tasks)
    for task in tasks:
        task.assignee = resolve_assignee(assignee)

    return tasks


def get_access_requests_groups(user: User):
    # if user doesn't have a permission to handle access requests - don't show them
    if not user.has_perm(zaken_handle_access.name):
        return []

    behandelaar_zaken = {
        zaak.url: zaak for zaak in search(user=user, behandelaar=user.username)
    }
    access_requests = AccessRequest.objects.filter(
        result="", zaak__in=list(behandelaar_zaken.keys())
    ).order_by("zaak", "requester__username")

    requested_zaken = []
    for zaak_url, group in groupby(access_requests, key=lambda a: a.zaak):
        requested_zaken.append(
            {
                "zaak_url": zaak_url,
                "access_requests": list(group),
                "zaak": behandelaar_zaken[zaak_url],
            }
        )
    return requested_zaken


def get_activity_groups(user: User, grouped_activities: dict) -> List[ActivityGroup]:
    zaak_urls = list(
        {activity_group["zaak_url"] for activity_group in grouped_activities}
    )
    es_results = search(user=user, urls=zaak_urls)
    zaken = {zaak.url: zaak for zaak in es_results}
    for activity_group in grouped_activities:
        activity_group["zaak"] = zaken.get(activity_group["zaak_url"])

    return grouped_activities
