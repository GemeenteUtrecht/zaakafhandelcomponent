import logging
from itertools import groupby
from typing import Dict, List, Optional
from urllib.request import Request

from django_camunda.camunda_models import factory
from django_camunda.client import get_client, get_client_class

from zac.accounts.models import AccessRequest, User
from zac.camunda.constants import AssigneeTypeChoices
from zac.camunda.data import Task
from zac.core.camunda.utils import resolve_assignee
from zac.core.permissions import zaken_handle_access
from zac.elasticsearch.searches import search_zaken

from .data import ActivityGroup, ChecklistAnswerGroup

logger = logging.getLogger(__name__)

CAMUNDA_CLIENT_CLASS = get_client_class()


def get_camunda_user_tasks(
    user: User, client: Optional[CAMUNDA_CLIENT_CLASS] = None
) -> List[Task]:
    return get_camunda_tasks(
        [f"{AssigneeTypeChoices.user}:{user.username}"], client=client
    )


def get_camunda_group_tasks(
    user: User, client: Optional[CAMUNDA_CLIENT_CLASS] = None
) -> List[Task]:
    return get_camunda_tasks(
        [
            f"{AssigneeTypeChoices.group}:{group}"
            for group in user.groups.all().values_list("name", flat=True)
        ],
        client=client,
    )


def get_camunda_tasks(
    assignees: List[str], client: Optional[CAMUNDA_CLIENT_CLASS] = None
) -> List[Task]:
    if not client:
        client = get_client()
    tasks = client.post("task", json={"assigneeIn": assignees})
    tasks = factory(Task, tasks)
    assignees = {assignee: resolve_assignee(assignee) for assignee in assignees}
    for task in tasks:
        task.assignee = assignees[task.assignee]
    return tasks


def get_camunda_variables(pis: List[str], client: CAMUNDA_CLIENT_CLASS) -> List[Dict]:
    return client.post(
        "variable-instance",
        json={
            "processInstanceIdIn": pis,
            "variableName": "zaakUrl",
        },
    )


def get_zaak_urls_from_tasks(
    tasks: List[Task], client: Optional[CAMUNDA_CLIENT_CLASS] = None
) -> Dict[str, str]:
    if not client:
        client = get_client()

    pids_and_tasks = {str(task.process_instance_id): task for task in tasks}
    variables = get_camunda_variables(list(pids_and_tasks.keys()), client=client)
    pids_and_urls = {
        variable["process_instance_id"]: variable["value"] for variable in variables
    }
    return {
        pids_and_tasks[process_instance_id].id: url
        for process_instance_id, url in pids_and_urls.items()
        if url
    }


def get_access_requests_groups(request: Request):
    # if user doesn't have a permission to handle access requests - don't show them
    if not request.user.has_perm(zaken_handle_access.name):
        return []

    behandelaar_zaken = {
        zaak.url: zaak
        for zaak in search_zaken(request=request, behandelaar=request.user.username)
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


def filter_on_existing_zaken(request: Request, groups: List[Dict]) -> List[Dict]:
    zaak_urls = list({group["zaak_url"] for group in groups})
    es_results = search_zaken(request=request, urls=zaak_urls)
    zaken = {zaak.url: zaak for zaak in es_results}

    # Make sure groups without a zaak in elasticsearch are not returned.
    filtered = []
    for group in groups:
        zaak = zaken.get(group["zaak_url"])
        if not zaak:
            logger.warning(
                "Can't find a zaak for url %s in elastic search." % group["zaak_url"]
            )
            continue

        group["zaak"] = zaak
        filtered.append(group)

    return filtered


def get_activity_groups(
    request: Request, grouped_activities: dict
) -> List[ActivityGroup]:
    activity_groups_with_zaak = filter_on_existing_zaken(request, grouped_activities)
    return [ActivityGroup(**group) for group in activity_groups_with_zaak]


def get_checklist_answers_groups(
    request: Request, grouped_checklist_answers: List[dict]
) -> List[ChecklistAnswerGroup]:
    checklist_answers_groups_with_zaak = filter_on_existing_zaken(
        request, grouped_checklist_answers
    )
    return [
        ChecklistAnswerGroup(**group) for group in checklist_answers_groups_with_zaak
    ]
