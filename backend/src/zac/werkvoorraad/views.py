from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from zds_client import ClientError
from zgw_consumers.concurrent import parallel

from zac.activities.models import Activity
from zac.core.services import get_zaak

from .api.utils import (
    get_access_requests_groups,
    get_behandelaar_zaken_unfinished,
    get_camunda_user_tasks,
)


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
