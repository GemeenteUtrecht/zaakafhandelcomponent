import json

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpResponseBadRequest, HttpResponseRedirect
from django.urls import reverse
from django.views.generic import FormView, TemplateView

from django_camunda.client import get_client

from ..camunda import complete_task, get_zaak_tasks
from ..forms import ClaimTaskForm
from ..services import _client_from_url, find_zaak, get_zaak

User = get_user_model()


class FetchTasks(LoginRequiredMixin, TemplateView):
    template_name = "core/includes/tasks.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        zaak_url = self.request.GET.get("zaak")
        if not zaak_url:
            raise ValueError("Expected zaak querystring parameter")

        context["tasks"] = get_zaak_tasks(zaak_url)
        context["zaak"] = get_zaak(zaak_url=zaak_url, zaak_uuid=None)
        return context


class PerformTaskView(LoginRequiredMixin, FormView):
    template_name = "core/zaak_task.html"

    def get(self, request, *args, **kwargs):
        self.zaak = find_zaak(
            bronorganisatie=kwargs["bronorganisatie"],
            identificatie=kwargs["identificatie"],
        )
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.zaak = find_zaak(
            bronorganisatie=kwargs["bronorganisatie"],
            identificatie=kwargs["identificatie"],
        )
        return super().post(request, *args, **kwargs)

    def _get_task(self):
        if not hasattr(self, "_task"):
            tasks = get_zaak_tasks(self.zaak.url)
            try:
                task = next(
                    (_task for _task in tasks if _task.id == self.kwargs["task_id"])
                )
            except StopIteration as exc:
                raise Http404("No such task for this zaak.") from exc
            self._task = task
        return self._task

    def get_form_class(self):
        task = self._get_task()
        return task.form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {"zaak": self.zaak, "task": self._get_task(),}
        )
        return context

    def get_success_url(self):
        return reverse(
            "core:zaak-detail",
            kwargs={
                "bronorganisatie": self.zaak.bronorganisatie,
                "identificatie": self.zaak.identificatie,
            },
        )

    def form_valid(self, form):
        task = self._get_task()

        zrc_client = _client_from_url(self.zaak.url)
        ztc_client = _client_from_url(self.zaak.zaaktype.url)

        zrc_jwt = zrc_client.auth.credentials()["Authorization"]
        ztc_jwt = ztc_client.auth.credentials()["Authorization"]

        variables = {
            "services": {
                "type": "Json",
                "value": json.dumps(
                    {"zrc": {"jwt": zrc_jwt}, "ztc": {"jwt": ztc_jwt},}
                ),
            },
            **{name: {"value": value} for name, value in form.cleaned_data.items()},
        }

        complete_task(task.id, variables)

        return super().form_valid(form)


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
