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
from zac.camunda.messages import get_messages
from zac.camunda.process_instances import get_process_instance
from zac.utils.decorators import retry

from ..camunda import get_process_zaak_url, get_task
from ..forms import ClaimTaskForm
from ..permissions import zaakproces_send_message, zaakproces_usertasks
from ..services import _client_from_url, fetch_zaaktype, get_roltypen, get_zaak
from ..task_handlers import HANDLERS, REVERSE_HANDLERS

logger = logging.getLogger(__name__)

User = get_user_model()


class SendMessage(PermissionRequiredMixin, FormView):
    template_name = "core/includes/messages.html"
    form_class = MessageForm
    permission_required = zaakproces_send_message.name

    def get_form(self, **kwargs):
        form = super().get_form(**kwargs)

        process_instance_id = form.data.get("process_instance_id")

        # no (valid) process instance ID -> get a form with no valid messages -> invalid
        # form submission
        if not process_instance_id:
            return form

        # set the valid process instance messages _if_ a process instance exists
        process_instance = get_process_instance(process_instance_id)
        if process_instance is None or process_instance.historical:
            return form

        messages = get_messages(process_instance.definition_id)
        form.set_message_choices(messages)

        return form

    def form_valid(self, form: MessageForm):
        # check permissions
        process_instance_id = form.cleaned_data["process_instance_id"]
        process_instance = get_process_instance(process_instance_id)

        zaak_url = process_instance.get_variable("zaakUrl")
        zaak = get_zaak(zaak_url=zaak_url)
        self.check_object_permissions(zaak)

        # build service variables to continue execution
        zrc_client = _client_from_url(zaak.url)
        ztc_client = _client_from_url(zaak.zaaktype)

        zrc_jwt = zrc_client.auth.credentials()["Authorization"]
        ztc_jwt = ztc_client.auth.credentials()["Authorization"]

        variables = {
            "services": {
                "zrc": {"jwt": zrc_jwt},
                "ztc": {"jwt": ztc_jwt},
            },
        }

        send_message(form.cleaned_data["message"], [process_instance.id], variables)

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
        kwargs = {
            "prefix": self.get_prefix(),
            "task": self._get_task(),
            "user": self.request.user,
        }
        if self.request.method in ("POST", "PUT"):
            kwargs.update(
                {
                    "data": self.request.POST,
                    "files": self.request.FILES,
                }
            )
        return kwargs


class UserTaskMixin:
    check_task_history = False

    def get_zaak(self):
        task = self._get_task()
        process_instance = get_process_instance(task.process_instance_id)
        zaak_url = get_process_zaak_url(process_instance)
        zaak = get_zaak(zaak_url=zaak_url)
        zaak.zaaktype = fetch_zaaktype(zaak.zaaktype)

        self.check_object_permissions(zaak)
        return zaak

    def _get_task(self, refresh=False):
        if not hasattr(self, "_task") or refresh:
            task = get_task(
                self.kwargs["task_id"], check_history=self.check_task_history
            )
            if task is None:
                raise Http404("No such task")
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

    def get_template_names(self):
        form_cls = self.get_form_class()
        if hasattr(form_cls, "template_name"):
            return [form_cls.template_name]
        return super().get_template_names()

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
        task = self._get_task()
        context.update(
            {
                "zaak": self.zaak,
                "task": task,
                "return_url": self.request.GET.get("returnUrl"),
            }
        )
        # check if we need to inject the external URL to open
        redirect_form_key = REVERSE_HANDLERS["core:redirect-task"]
        if task.form_key == redirect_form_key:
            context.update({"open_url": self.request.session.get("open_url")})
        return context

    def get_success_url(self):
        return_url = self.request.POST.get("return_url")

        if return_url and is_safe_url(
            return_url,
            allowed_hosts=[self.request.get_host()],
            require_https=self.request.is_secure(),
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

        formset_vars = formset.get_process_variables() if formset else {}

        variables = {
            "services": services,
            **form.get_process_variables(),
            **formset_vars,
        }

        complete_task(task.id, variables)

        return super().form_valid(form)


class RedirectTaskView(PermissionRequiredMixin, UserTaskMixin, RedirectView):
    permission_required = zaakproces_usertasks.name
    check_task_history = True

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
            return_url = reverse(
                "core:zaak-detail",
                kwargs={
                    "bronorganisatie": self.zaak.bronorganisatie,
                    "identificatie": self.zaak.identificatie,
                },
            )
        else:
            # return back to the zaak when done
            return_url = self.request.build_absolute_uri(self.request.path)

        # prepare state so that we know what to do
        state = {
            "user_id": self.request.user.id,
            "task_id": str(task.id),
        }

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
                extra={
                    "expected": user.id,
                    "received": state.get("user_id"),
                },
            )
            raise PermissionDenied("State is for a different user")

        # now check that the assignee of the task is the correct user
        task = self._get_task()
        if str(task.id) != state.get("task_id"):
            logger.warning(
                "Invalid Task ID in state",
                extra={
                    "expected": str(task.id),
                    "received": state.get("task_id"),
                },
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

    @retry(
        times=3,
        exceptions=(requests.HTTPError,),
        condition=lambda exc: exc.response.status_code == 500,
        delay=0.5,
    )
    def complete_task(self) -> HttpResponseRedirect:
        """
        Complete the UserTask in Camunda.

        Various race conditions apply - it *may* be that the UserTask was already
        completed by a webhook handler. In that case, the task is historical and we
        don't need to try to complete it.

        It may also be that both the webhook handlers and this call are in a race
        condition, after which Camunda will throw a 500 error for one of both and
        roll back that transaction. The @retry decorator handles this, which leads to
        the task refresh now yielding a historical task instead.
        """
        task = self._get_task(refresh=True)
        if not task.historical:
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

        # check if the betrokkene already exists
        existing = zrc_client.list(
            "rol",
            query_params={
                "zaak": zaak.url,
                "betrokkeneIdentificatie__medewerker__identificatie": self.request.user.username,
            },
        )
        if existing["count"]:
            return

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
        # check permissions
        task = form.cleaned_data["task_id"]
        process_instance = get_process_instance(task.process_instance_id)
        zaak_url = get_process_zaak_url(process_instance)

        zaak = get_zaak(zaak_url=zaak_url)
        self.check_object_permissions(zaak)

        zaak.zaaktype = fetch_zaaktype(zaak.zaaktype)

        # claim in Camunda
        camunda_client = get_client()
        camunda_client.post(
            f"task/{task.id}/claim", json={"userId": self.request.user.username}
        )

        # register the 'medewerker' if sufficient information
        # TODO: celery!
        self._create_rol(zaak)

        _next = form.cleaned_data["next"] or self.request.META["HTTP_REFERER"]
        return HttpResponseRedirect(_next)

    def form_invalid(self, form):
        errors = form.errors.as_json()
        response = HttpResponseBadRequest(
            content=errors.encode("utf-8"),
            content_type="application/json",
        )
        return response
