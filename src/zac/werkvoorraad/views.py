from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from zgw_consumers.concurrent import parallel

from zac.activities.models import Activity
from zac.core.services import get_zaak


class SummaryView(LoginRequiredMixin, TemplateView):
    template_name = "index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # TODO: zaken that current user is behandelaar in
        # TODO: Camunda user tasks

        activity_groups = Activity.objects.as_werkvoorraad(user=self.request.user)

        def set_zaak(activity_group):
            activity_group["zaak"] = get_zaak(zaak_url=activity_group["zaak_url"])

        with parallel() as executor:
            for activity_group in activity_groups:
                executor.submit(set_zaak, activity_group)

        context.update(
            {"adhoc_activities": activity_groups,}
        )

        return context
