from itertools import groupby
from typing import List

from django_camunda.camunda_models import factory
from django_camunda.client import get_client

from zac.accounts.models import AccessRequest, User
from zac.camunda.data import Task
from zac.core.permissions import zaken_handle_access
from zac.core.services import get_behandelaar_zaken
from zgw.models.zrc import Zaak


def get_behandelaar_zaken_unfinished(user: User, ordering: List = []) -> List[Zaak]:
    """
    Retrieve the un-finished zaken where `user` is a medewerker in the role of behandelaar.
    """
    zaken = get_behandelaar_zaken(user, ordering=ordering)
    unfinished_zaken = [zaak for zaak in zaken if not zaak.einddatum]
    return unfinished_zaken


def get_camunda_user_tasks(user: User):
    client = get_client()
    tasks = client.get("task", {"assignee": user.username})

    tasks = factory(Task, tasks)
    for task in tasks:
        task.assignee = user

    return tasks


def get_access_requests_groups(user: User):
    # if user doesn't have a permission to handle access requests - don't show them
    if not user.has_perm(zaken_handle_access.name):
        return []

    behandelaar_zaken = {zaak.url: zaak for zaak in get_behandelaar_zaken(user)}
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
