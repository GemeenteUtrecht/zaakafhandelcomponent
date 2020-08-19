from typing import List

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from django_camunda.camunda_models import Task, factory
from django_camunda.client import get_client
from zgw_consumers.concurrent import parallel

from zac.accounts.models import User
from zac.accounts.permissions import UserPermissions
from zac.activities.models import Activity
from zac.core.services import get_zaak, get_zaken
from zgw.models.zrc import Zaak


def get_behandelaar_zaken(user: User) -> List[Zaak]:
    """
    Retrieve the un-finished zaken where `user` is a medewerker in the role of behandelaar.
    """
    medewerker_id = user.username
    user_perms = UserPermissions(user)
    behandelaar_zaken = get_zaken(
        user_perms,
        skip_cache=True,
        find_all=True,
        **{
            "rol__betrokkeneIdentificatie__medewerker__identificatie": medewerker_id,
            "rol__omschrijvingGeneriek": "behandelaar",
            "rol__betrokkeneType": "medewerker",
        }
    )
    unfinished_zaken = [zaak for zaak in behandelaar_zaken if not zaak.einddatum]
    return sorted(unfinished_zaken, key=lambda zaak: zaak.deadline)


def get_camunda_user_tasks(user: User):
    client = get_client()
    tasks = client.get("task", {"assignee": user.username})

    tasks = factory(Task, tasks)
    for task in tasks:
        task.assignee = user

    return tasks


class SummaryView(LoginRequiredMixin, TemplateView):
    template_name = "index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # TODO: Camunda user tasks

        activity_groups = Activity.objects.as_werkvoorraad(user=self.request.user)

        def set_zaak(activity_group):
            activity_group["zaak"] = get_zaak(zaak_url=activity_group["zaak_url"])

        with parallel() as executor:
            for activity_group in activity_groups:
                executor.submit(set_zaak, activity_group)

        context.update(
            {
                "zaken": get_behandelaar_zaken(self.request.user),
                "adhoc_activities": activity_groups,
                "user_tasks": get_camunda_user_tasks(self.request.user),
            }
        )

        return context
