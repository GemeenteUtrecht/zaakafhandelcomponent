from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from django_camunda.camunda_models import Task, factory
from django_camunda.client import get_client


class FetchTasks(LoginRequiredMixin, TemplateView):
    template_name = "core/includes/tasks.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        zaak_url = self.request.GET.get("zaak")
        if not zaak_url:
            raise ValueError("Expected zaak querystring parameter")

        context["tasks"] = self._fetch_tasks(zaak_url)
        return context

    def _fetch_tasks(self, zaak_url: str):
        client = get_client()
        tasks = client.get("task", {"processVariables": f"zaakUrl_eq_{zaak_url}"},)
        return factory(Task, tasks)
