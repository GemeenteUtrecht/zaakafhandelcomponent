import base64
import json
import logging
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, SuspiciousOperation
from django.http import Http404, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import is_safe_url
from django.views import View
from django.views.generic import FormView, RedirectView

import requests
from django_camunda.api import complete_task, get_task_variable, send_message
from django_camunda.client import get_client

from zac.accounts.mixins import PermissionRequiredMixin
from zac.camunda.forms import DummyForm, MessageForm
from zac.camunda.messages import get_process_definition_messages

from ..camunda import get_process_zaak_url, get_task, get_zaak_tasks
from ..forms import ClaimTaskForm
from ..permissions import zaakproces_send_message, zaakproces_usertasks
from ..services import _client_from_url, fetch_zaaktype, get_roltypen, get_zaak
from ..task_handlers import HANDLERS

logger = logging.getLogger(__name__)

User = get_user_model()


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

    def form_valid(self, form: MessageForm):
        # build service variables to continue execution
        zaak = get_zaak(zaak_url=form.cleaned_data["zaak_url"])
        self.check_object_permissions(zaak)

        zrc_client = _client_from_url(zaak.url)
        ztc_client = _client_from_url(zaak.zaaktype)

        zrc_jwt = zrc_client.auth.credentials()["Authorization"]
        ztc_jwt = ztc_client.auth.credentials()["Authorization"]

        variables = {
            "services": {"zrc": {"jwt": zrc_jwt}, "ztc": {"jwt": ztc_jwt},},
        }

        send_message(form.cleaned_data["message"], form._instance_ids, variables)

        _next = self.request.META["HTTP_REFERER"]
        if is_safe_url(_next, [self.request.get_host()], settings.IS_HTTPS):
            return HttpResponseRedirect(_next)
        raise SuspiciousOperation("Unsafe HTTP_REFERER detected")


class FormSetMixin:
    def get_formset_class(self):
        task = self._get_task()
        return task.form.get("formset") if task.form else None

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
        task = self._get_task()
        zaak_url = get_process_zaak_url(task.process_instance_id)
        zaak = get_zaak(zaak_url=zaak_url)
        self.check_object_permissions(zaak)
        return zaak

    def _get_task(self):
        if not hasattr(self, "_task"):
            try:
                task = get_task(self.kwargs["task_id"])
            except requests.RequestException as exc:
                raise Http404("The task was not found") from exc
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
        response = super().post(request, *args, **kwargs)
        if "open_url" in self.request.session:
            del self.request.session["open_url"]
        return response

    def get_form_class(self):
        task = self._get_task()
        return task.form["form"] if task.form else DummyForm

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
            {
                "zaak": self.zaak,
                "task": self._get_task(),
                "open_url": self.request.session.get("open_url"),
                "return_url": self.request.GET.get("returnUrl"),
            }
        )
        return context

    def get_success_url(self):
        return_url = self.request.POST.get("return_url")
        if return_url and is_safe_url(
            return_url, allowed_hosts=[self.request.get_host()]
        ):
            return return_url

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

    def get(self, request, *args, **kwargs):
        # check if we're returning from an external application - indicated by the
        # presence of the state parameter
        if "state" in self.request.GET:
            self.zaak = self.get_zaak()
            self.validate_state(self.request.GET["state"])
            return self.complete_task()
        return super().get(request, *args, **kwargs)

    def get_redirect_url(self, *args, **kwargs):
        self.zaak = self.get_zaak()
        task = self._get_task()

        # prepare the callback URL
        redirect_url = get_task_variable(task.id, "redirectTo")
        new_window = get_task_variable(task.id, "openInNewWindow", False)

        if new_window:
            # TODO: session is annoying, quick workaround
            self.request.session["open_url"] = redirect_url
            redirect_url = reverse("core:perform-task", kwargs=self.kwargs)

        # prepare state so that we know what to do
        state = {
            "user_id": self.request.user.id,
            "task_id": str(task.id),
        }

        # return back to the zaak when do
        return_url = self.request.build_absolute_uri(self.request.path)
        encoded_state = urlencode(
            {"state": base64.b64encode(json.dumps(state).encode("utf-8"))}
        )
        return_url = f"{return_url}?{encoded_state}"

        # encapsulate that entire return URL as redirect parameter
        qs = urlencode({"returnUrl": return_url})

        # we do not check for safe URLs here, as the URL should have been sanitized from
        # the process... can't white list this, since we go to external applications
        # TODO: we should generate one-time-token URLs etc.
        return f"{redirect_url}?{qs}"

    def validate_state(self, encoded_state: str) -> dict:
        try:
            state = json.loads(base64.b64decode(encoded_state))
        except Exception:
            logger.warning("Tampered state", exc_info=True, extra={"state": state})
            raise PermissionDenied("State parameter is tampered with")

        user = self.request.user

        if user.id != state.get("user_id"):
            logger.warning(
                "Invalid user in state",
                extra={"expected": user.id, "received": state.get("user_id"),},
            )
            raise PermissionDenied("State is for a different user")

        # now check that the assignee of the task is the correct user
        task = self._get_task()
        if str(task.id) != state.get("task_id"):
            logger.warning(
                "Invalid Task ID in state",
                extra={"expected": str(task.id), "received": state.get("task_id"),},
            )
            raise PermissionDenied("Invalid task ID in state")

        if not task.assignee:
            logger.warning(
                "Task did not have an assignee - can not verify ownership!",
                extra={"task": str(task.id)},
            )
            return

        if task.assignee != user:
            raise PermissionDenied("Current user is not assignee of task.")

        return state

    def complete_task(self) -> HttpResponseRedirect:
        task = self._get_task()
        complete_task(task.id, {})
        zaak_detail = reverse(
            "core:zaak-detail",
            kwargs={
                "bronorganisatie": self.zaak.bronorganisatie,
                "identificatie": self.zaak.identificatie,
            },
        )
        return HttpResponseRedirect(zaak_detail)


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
