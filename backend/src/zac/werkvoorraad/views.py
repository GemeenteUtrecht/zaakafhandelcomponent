from itertools import groupby
from typing import List

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from django_camunda.camunda_models import Task, factory
from django_camunda.client import get_client
from zds_client import ClientError
from zgw_consumers.concurrent import parallel

from zac.accounts.models import AccessRequest, User
from zac.activities.models import Activity
from zac.core.permissions import zaken_handle_access
from zac.core.services import get_behandelaar_zaken, get_zaak
from zgw.models.zrc import Zaak


def get_behandelaar_zaken_unfinished(user: User) -> List[Zaak]:
    """
    Retrieve the un-finished zaken where `user` is a medewerker in the role of behandelaar.
    """
    zaken = get_behandelaar_zaken(user)
    unfinished_zaken = [zaak for zaak in zaken if not zaak.einddatum]
    return sorted(unfinished_zaken, key=lambda zaak: zaak.deadline)


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


class SummaryView(LoginRequiredMixin, TemplateView):
    template_name = "index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # TODO: Camunda user tasks

        activity_groups = Activity.objects.as_werkvoorraad(user=self.request.user)

        def set_zaak(group):
            try:
                group["zaak"] = get_zaak(zaak_url=group["zaak_url"])
            except ClientError as exc:
                if exc.args[0]["status"] == 404:  # zaak deleted / no longer exists
                    return
                raise

        with parallel() as executor:
            for activity_group in activity_groups:
                executor.submit(set_zaak, activity_group)

        context.update(
            {
                "zaken": get_behandelaar_zaken_unfinished(self.request.user),
                "adhoc_activities": [
                    group for group in activity_groups if "zaak" in group
                ],
                "user_tasks": get_camunda_user_tasks(self.request.user),
                "access_requests": get_access_requests_groups(self.request.user),
            }
        )

        return context
