from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from django.views.generic import FormView, TemplateView

from django_camunda.camunda_models import Task, factory
from django_camunda.client import get_client

from ..forms import ClaimTaskForm

User = get_user_model()


def _resolve_assignee(username: str) -> User:
    user = User.objects.get(username=username)
    return user


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
        tasks = factory(Task, tasks)
        for task in tasks:
            if task.assignee:
                task.assignee = _resolve_assignee(task.assignee)
        return tasks


class ClaimTaskView(LoginRequiredMixin, FormView):
    form_class = ClaimTaskForm

    def form_valid(self, form: ClaimTaskForm):
        _next = form.cleaned_data["next"] or self.request.META["HTTP_REFERER"]
        task_id = form.cleaned_data["task_id"]

        client = get_client()
        client.post(
            f"task/{task_id}/claim", json={"userId": self.request.user.username,}
        )

        return HttpResponseRedirect(_next)

    def form_invalid(self, form):
        errors = form.errors.as_json()
        response = HttpResponseBadRequest(
            content=errors.encode("utf-8"), content_type="application/json",
        )
        return response
