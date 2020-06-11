from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import SuspiciousOperation
from django.http import Http404, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import is_safe_url
from django.views import View
from django.views.generic import FormView, RedirectView, TemplateView

from django_camunda.api import (
    complete_task,
    get_process_instance_variable,
    send_message,
)
from django_camunda.client import get_client

from zac.accounts.mixins import PermissionRequiredMixin
from zac.camunda.forms import MessageForm
from zac.camunda.messages import get_process_definition_messages
from zac.camunda.models import UserTaskCallback

from ..camunda import get_zaak_tasks
from ..forms import ClaimTaskForm
from ..permissions import zaakproces_send_message, zaakproces_usertasks
from ..services import (
    _client_from_url,
    fetch_zaaktype,
    find_zaak,
    get_roltypen,
    get_zaak,
)
from ..task_handlers import HANDLERS
from .utils import get_zaak_from_query

User = get_user_model()


class FetchTasks(PermissionRequiredMixin, TemplateView):
    template_name = "core/includes/tasks.html"
    permission_required = zaakproces_usertasks.name

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        zaak = get_zaak_from_query(self.request)
        self.check_object_permissions(zaak)

        context["tasks"] = get_zaak_tasks(zaak.url)
        context["zaak"] = zaak
        return context


class FetchMessages(PermissionRequiredMixin, TemplateView):
    template_name = "core/includes/messages.html"
    permission_required = zaakproces_send_message.name

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        zaak = get_zaak_from_query(self.request)
        self.check_object_permissions(zaak)

        definitions = get_process_definition_messages(zaak.url)
        context["forms"] = [
            definition.get_form(initial={"zaak_url": zaak.url})
            for definition in definitions
        ]
        context["zaak"] = zaak
        return context


class SendMessage(PermissionRequiredMixin, FormView):
    template_name = "core/includes/messages.html"
    form_class = MessageForm
    permission_required = zaakproces_send_message.name

    def get_form(self, **kwargs):
        form = super().get_form(**kwargs)
        definitions = get_process_definition_messages(form.data["zaak_url"])
        definition = next(
            (
                definition
                for definition in definitions
                if definition.id == form.data["definition_id"]
            ),
            None,
        )

        if definition is None:
            return form  # the empty message names will fail validation

        form.set_message_choices(definition.message_names)
        form._instance_ids = definition.instance_ids

        return form

    def form_valid(self, form: ClaimTaskForm):
        # build service variables to continue execution
        zaak = get_zaak(zaak_url=form.cleaned_data["zaak_url"])
        self.check_object_permissions(zaak)

        zrc_client = _client_from_url(zaak.url)
        ztc_client = _client_from_url(zaak.zaaktype)

        zrc_jwt = zrc_client.auth.credentials()["Authorization"]
        ztc_jwt = ztc_client.auth.credentials()["Authorization"]

        variables = {
            "services": {"zrc": {"jwt": zrc_jwt}, "ztc": {"jwt": ztc_jwt},},
            **form.cleaned_data,
        }

        send_message(form.cleaned_data["message"], form._instance_ids, variables)

        _next = self.request.META["HTTP_REFERER"]
        if is_safe_url(_next, [self.request.get_host()], settings.IS_HTTPS):
            return HttpResponseRedirect(_next)
        raise SuspiciousOperation("Unsafe HTTP_REFERER detected")


class FormSetMixin:
    def get_formset_class(self):
        task = self._get_task()
        return task.form.get("formset")

    def get_formset(self):
        formset_class = self.get_formset_class()
        if not formset_class:
            return

        formset = formset_class(**self.get_formset_kwargs())
        return formset

    def get_context_data(self, **kwargs):
        if "formset" not in kwargs:
            kwargs["formset"] = self.get_formset()

        return super().get_context_data(**kwargs)

    def get_formset_kwargs(self):
        kwargs = {"task": self._get_task(), "user": self.request.user}

        if self.request.method == "POST":
            kwargs.update(
                {"data": self.request.POST.copy(), "files": self.request.FILES}
            )
        return kwargs


class UserTaskMixin:
    def get_zaak(self):
        zaak = find_zaak(
            bronorganisatie=self.kwargs["bronorganisatie"],
            identificatie=self.kwargs["identificatie"],
        )
        self.check_object_permissions(zaak)
        return zaak

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


class RouteTaskView(PermissionRequiredMixin, UserTaskMixin, View):
    """
    Analyze the user task definition and redirect to the appropriate page.
    """

    permission_required = zaakproces_usertasks.name

    def get(self, request, *args, **kwargs):
        self.zaak = self.get_zaak()
        task = self._get_task()

        handler = HANDLERS.get(task.form_key, "core:perform-task")
        return redirect(handler, *args, **kwargs)


class PerformTaskView(PermissionRequiredMixin, FormSetMixin, UserTaskMixin, FormView):
    template_name = "core/zaak_task.html"
    permission_required = zaakproces_usertasks.name

    def get(self, request, *args, **kwargs):
        self.zaak = self.get_zaak()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.zaak = self.get_zaak()
        return super().post(request, *args, **kwargs)

    def get_form_class(self):
        task = self._get_task()
        return task.form["form"]

    def get_form_kwargs(self):
        base = super().get_form_kwargs()
        task = self._get_task()
        extra = {"task": task}
        return {**base, **extra}

    def get_form(self, *args, **kwargs):
        form = super().get_form(*args, **kwargs)
        form.set_context({"request": self.request, "view": self})
        return form

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
        formset = self.get_formset()

        if formset and not formset.is_valid():
            return self.render_to_response(
                self.get_context_data(form=form, formset=formset)
            )

        form.on_submission()

        if formset and formset.is_valid():
            formset.on_submission(form=form)

        task = self._get_task()

        zrc_client = _client_from_url(self.zaak.url)
        ztc_client = _client_from_url(self.zaak.zaaktype.url)

        zrc_jwt = zrc_client.auth.credentials()["Authorization"]
        ztc_jwt = ztc_client.auth.credentials()["Authorization"]

        services = {
            "zrc": {"jwt": zrc_jwt},
            "ztc": {"jwt": ztc_jwt},
        }

        variables = {
            "services": services,
            **form.get_process_variables(),
        }

        complete_task(task.id, variables)

        return super().form_valid(form)


class RedirectTaskView(PermissionRequiredMixin, UserTaskMixin, RedirectView):
    permission_required = zaakproces_usertasks.name

    def get_redirect_url(self, *args, **kwargs):
        self.zaak = self.get_zaak()
        task = self._get_task()

        # prepare the callback URL
        if settings.DEBUG:
            redirect_url = (
                "http://localhost:8000/kownsl/50f99778-32d7-423f-8032-fa6eadfc56dd/"
            )
        else:
            redirect_url = get_process_instance_variable(
                task.process_instance_id, "redirectTo"
            )
        expected_callback = UserTaskCallback.objects.create(task_id=task.id)

        # return back to the zaak when do
        success_url = self.request.build_absolute_uri(
            reverse(
                "core:zaak-detail",
                kwargs={
                    "bronorganisatie": kwargs["bronorganisatie"],
                    "identificatie": kwargs["identificatie"],
                },
            )
        )
        callback_url = self.request.build_absolute_uri(
            reverse(
                "camunda:user-task-callback",
                kwargs={"callback_id": expected_callback.callback_id},
            )
        )

        qs = urlencode({"redirectUrl": success_url, "callbackUrl": callback_url})

        # we do not check of safe URLs here, as the URL should have been sanitized from
        # the process... can't white list this, since we go to external applications
        # TODO: we should generate one-time-token URLs etc.
        return f"{redirect_url}?{qs}"


class ClaimTaskView(PermissionRequiredMixin, FormView):
    form_class = ClaimTaskForm
    permission_required = zaakproces_usertasks.name

    def _create_rol(self, zaak):
        # fetch roltype
        roltypen = get_roltypen(zaak.zaaktype, omschrijving_generiek="behandelaar")
        if not roltypen:
            return
        roltype = roltypen[0]

        zrc_client = _client_from_url(zaak.url)
        voorletters = " ".join(
            [part[0] for part in self.request.user.first_name.split()]
        )
        data = {
            "zaak": zaak.url,
            "betrokkeneType": "medewerker",
            "roltype": roltype.url,
            "roltoelichting": "task claiming",
            "betrokkeneIdentificatie": {
                "identificatie": self.request.user.username,
                "achternaam": self.request.user.last_name,
                "voorletters": voorletters,
            },
        }
        zrc_client.create("rol", data)

    def form_valid(self, form: ClaimTaskForm):
        zaak = get_zaak(zaak_url=form.cleaned_data["zaak"])
        self.check_object_permissions(zaak)

        _next = form.cleaned_data["next"] or self.request.META["HTTP_REFERER"]
        task_id = form.cleaned_data["task_id"]
        zaak_url = form.cleaned_data["zaak"]
        zaak = get_zaak(zaak_url=zaak_url)
        zaak.zaaktype = fetch_zaaktype(zaak.zaaktype)

        camunda_client = get_client()
        camunda_client.post(
            f"task/{task_id}/claim", json={"userId": self.request.user.username}
        )

        self._create_rol(zaak)

        return HttpResponseRedirect(_next)

    def form_invalid(self, form):
        errors = form.errors.as_json()
        response = HttpResponseBadRequest(
            content=errors.encode("utf-8"), content_type="application/json",
        )
        return response
