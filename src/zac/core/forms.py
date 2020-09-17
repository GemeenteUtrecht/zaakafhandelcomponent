import itertools
import logging
from typing import Dict, List, Tuple

from django import forms
from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.html import format_html
from django.utils.http import is_safe_url
from django.utils.translation import ugettext_lazy as _

from django_camunda.api import get_process_instance_variable
from django_camunda.camunda_models import Task
from zgw_consumers.api_models.catalogi import ZaakType

from zac.accounts.constants import AccessRequestResult
from zac.accounts.models import AccessRequest, User
from zac.camunda.forms import TaskFormMixin
from zac.contrib.kownsl.api import create_review_request
from zac.utils.sorting import sort

from .fields import DocumentsMultipleChoiceField
from .services import (
    get_documenten,
    get_resultaattypen,
    get_rollen,
    get_statustypen,
    get_zaak,
    zet_resultaat,
    zet_status,
)

logger = logging.getLogger(__name__)


def get_zaaktype_choices(zaaktypen: List[ZaakType]) -> List[Tuple[str, list]]:
    zaaktypen = sort(zaaktypen, ["omschrijving", "-versiedatum"])
    choices = []
    for key, group in itertools.groupby(zaaktypen, lambda zt: zt.omschrijving):
        group_choices = [
            (zt.url, _("Version {zt.versiedatum} - {zt.identificatie}").format(zt=zt))
            for zt in group
        ]
        choices.append((key, group_choices))

    return choices


class ZakenFilterForm(forms.Form):
    identificatie = forms.CharField(
        label=_("identificatie"),
        required=False,
    )
    zaaktypen = forms.MultipleChoiceField(
        label=_("zaaktypen (huidige versies)"),
        required=False,
        choices=[],
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, **kwargs):
        zaaktypen = kwargs.pop("zaaktypen")
        super().__init__(*args, **kwargs)

        self.fields["zaaktypen"].choices = get_zaaktype_choices(zaaktypen)

    def as_filters(self) -> dict:
        assert self.cleaned_data
        zaaktypen = self.cleaned_data.get("zaaktypen")
        identificatie = self.cleaned_data.get("identificatie")

        filters = {}
        if zaaktypen:
            filters["zaaktypen"] = zaaktypen
        if identificatie:
            filters["identificatie"] = identificatie

        return filters


class ClaimTaskForm(forms.Form):
    task_id = forms.UUIDField(required=True)
    next = forms.CharField(required=False)

    def clean_next(self) -> str:
        next_url = self.cleaned_data["next"]
        if not next_url:
            return ""

        safe_url = is_safe_url(
            next_url, settings.ALLOWED_HOSTS, require_https=settings.IS_HTTPS
        )
        if not safe_url:
            raise forms.ValidationError(_("The redirect URL is untrusted."))
        return next_url

    def clean_task_id(self) -> Task:
        from .camunda import get_task

        task_id = self.cleaned_data["task_id"]
        task = get_task(task_id)
        if task is None:
            raise forms.ValidationError(_("Invalid task referenced."))
        return task


class ZaakAfhandelForm(forms.Form):
    resultaattype = forms.TypedChoiceField(
        required=False,
        label="Resultaat",
        widget=forms.RadioSelect,
    )
    result_remarks = forms.CharField(
        required=False,
        label="Toelichting",
        widget=forms.Textarea,
    )
    close_zaak = forms.BooleanField(
        required=False,
        label="Zaak afsluiten?",
        help_text="Sluit de zaak af als er een resultaat gezet is.",
    )
    close_zaak_remarks = forms.CharField(
        required=False,
        label="Toelichting bij afsluiten zaak",
        widget=forms.Textarea,
    )

    def __init__(self, *args, **kwargs):
        self.zaak = kwargs.pop("zaak")
        self.can_set_result = kwargs.pop("can_set_result")
        self.can_close = kwargs.pop("can_close")

        super().__init__(*args, **kwargs)

        if self.can_set_result:
            # fetch the possible result types
            zaaktype = self.zaak.zaaktype

            _resultaattypen = {rt.url: rt for rt in get_resultaattypen(zaaktype)}
            resultaattype_choices = [
                (url, resultaattype.omschrijving)
                for url, resultaattype in _resultaattypen.items()
            ]
            self.fields["resultaattype"].choices = resultaattype_choices
            self.fields["resultaattype"].coerce = _resultaattypen.get
        else:
            del self.fields["resultaattype"]
            del self.fields["result_remarks"]

        if not self.can_close:
            del self.fields["close_zaak"]
            del self.fields["close_zaak_remarks"]

    def clean_close_zaak(self):
        close_zaak = self.cleaned_data["close_zaak"]
        if close_zaak and self.zaak.einddatum:
            raise forms.ValidationError(
                _("De zaak is al gesloten en kan niet opnieuw gesloten worden.")
            )
        return close_zaak

    def save(self, user):
        """
        Commit the changes to the backing API.
        """
        if not any((self.can_set_result, self.can_close)):
            return

        resultaattype = self.cleaned_data.get("resultaattype")

        if self.can_set_result and resultaattype:
            zet_resultaat(self.zaak, resultaattype, self.cleaned_data["result_remarks"])

        if self.can_close and self.cleaned_data["close_zaak"]:
            statustypen = get_statustypen(self.zaak.zaaktype)
            last_statustype = sorted(statustypen, key=lambda st: st.volgnummer)[-1]
            zet_status(
                self.zaak, last_statustype, self.cleaned_data["close_zaak_remarks"]
            )


def _repr(doc):
    download_path = reverse(
        "core:download-document",
        kwargs={
            "bronorganisatie": doc.bronorganisatie,
            "identificatie": doc.identificatie,
        },
    )
    name = doc.titel or doc.bestandsnaam
    extra = f"({doc.informatieobjecttype.omschrijving}, {doc.get_vertrouwelijkheidaanduiding_display()})"
    title = f"v{doc.versie}"
    return format_html(
        '<a href="{download_path}" class="link" target="_blank" '
        'rel="noopener nofollow">{name}</a> <span title="{title}">{extra}</span>',
        download_path=download_path,
        name=name,
        extra=extra,
        title=title,
    )


class SelectDocumentsForm(TaskFormMixin, forms.Form):
    """
    Select (a subset) of documents belonging to a Zaak.
    """

    documenten = DocumentsMultipleChoiceField(
        label=_("Selecteer de relevante documenten"),
        help_text=_(
            "Dit zijn de documenten die bij de zaak horen. Selecteer de relevante "
            "documenten voor het vervolg van het proces."
        ),
    )

    template_name = "core/select_documents.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # retrieve process instance variables
        zaak_url = get_process_instance_variable(
            self.task.process_instance_id, "zaakUrl"
        )
        self.fields["documenten"].zaak = zaak_url


class SelectUsersForm(TaskFormMixin, forms.Form):
    """
    Select a (subset of) application users.
    """

    users = forms.ModelMultipleChoiceField(
        required=True,
        label=_("Users"),
        queryset=User.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple,
    )

    def get_process_variables(self) -> Dict[str, List[str]]:
        user_names = [user.username for user in self.cleaned_data["users"]]
        return {"users": user_names}


class ConfigureReviewRequestForm(TaskFormMixin, forms.Form):
    """
    Select the documents from a zaak and users that will perform the review.

    This is essentially the combination of :class:`SelectDocumentsForm` and
    :class:`SelectUsersForm`, which deprecates these.
    """

    documenten = forms.MultipleChoiceField(
        label=_("Selecteer de relevante documenten"),
        help_text=_(
            "Dit zijn de documenten die bij de zaak horen. Selecteer de relevante "
            "documenten voor het vervolg van het proces."
        ),
        widget=forms.CheckboxSelectMultiple,
    )

    users = forms.ModelMultipleChoiceField(
        required=True,
        label=_("Users"),
        queryset=User.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple,
        help_text=_("Selecteer de gewenste adviseurs."),
    )

    _review_type = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # retrieve process instance variables
        self.zaak_url = get_process_instance_variable(
            self.task.process_instance_id, "zaakUrl"
        )
        zaak = get_zaak(zaak_url=self.zaak_url)
        documenten, _ = get_documenten(zaak)

        self.fields["documenten"].choices = [
            (doc.url, _repr(doc)) for doc in documenten
        ]

    def get_process_variables(self) -> Dict[str, List[str]]:
        assert self.is_valid(), "Form must be valid"
        user_names = [user.username for user in self.cleaned_data["users"]]
        return {
            "users": user_names,
            "kownslReviewRequestId": self.cleaned_data["review_request"],
            "kownslFrontendUrl": self.cleaned_data["kownslFrontendUrl"],
        }

    def on_submission(self):
        assert self._review_type, "Subclasses must define a '_review_type'"

        review_request = create_review_request(
            self.zaak_url,
            documents=self.cleaned_data["documenten"],
            review_type=self._review_type,
            num_assigned_users=len(self.cleaned_data["users"]),
        )
        self.cleaned_data["review_request"] = str(review_request.id)
        self.cleaned_data["kownslFrontendUrl"] = review_request.frontend_url


class ConfigureAdviceRequestForm(ConfigureReviewRequestForm):
    """
    Create an "advice" type of review request on valid submission.
    """

    _review_type = "advice"


class ConfigureApprovalRequestForm(ConfigureReviewRequestForm):
    """
    Create an "approval" type of review request on valid submission.
    """

    _review_type = "approval"


class AccessRequestCreateForm(forms.ModelForm):
    """
    Create access request for a particular zaak
    """

    class Meta:
        model = AccessRequest
        fields = ("comment",)

    def __init__(self, *args, **kwargs):
        self.requester = kwargs.pop("requester")
        self.zaak = kwargs.pop("zaak")

        super().__init__(*args, **kwargs)

    def get_behandelaars(self):
        rollen = get_rollen(self.zaak)
        behandelaar_usernames = [
            rol.betrokkene_identificatie.get("identificatie")
            for rol in rollen
            if rol.betrokkene_type == "medewerker"
            and rol.omschrijving_generiek == "behandelaar"
        ]
        return User.objects.filter(username__in=behandelaar_usernames)

    def clean(self):
        cleaned_data = super().clean()
        if self.requester.initiated_requests.filter(zaak=self.zaak.url).exists():
            raise forms.ValidationError(
                _("You've already requested access for this zaak")
            )

        return cleaned_data

    def save(self, *args, **kwargs):
        self.instance.requester = self.requester
        self.instance.zaak = self.zaak.url
        request_access = super().save()

        behandelaars = self.get_behandelaars()
        if behandelaars:
            request_access.handlers.add(*behandelaars)

        return request_access


class AccessRequestHandleForm(forms.ModelForm):
    """
    Reject or approve access requests for a particular zaak
    """

    checked = forms.BooleanField(required=False)

    class Meta:
        model = AccessRequest
        fields = ("checked",)

    def __init__(self, **kwargs):
        self.request = kwargs.pop("request")

        super().__init__(**kwargs)

    def send_email(self):
        user = self.instance.requester

        if not user.email:
            logger.warning("Email to %s can't be sent - no known e-mail", user)
            return

        action = (
            "approved"
            if self.instance.result == AccessRequestResult.approve
            else "rejected"
        )
        zaak = get_zaak(zaak_url=self.instance.zaak)
        zaak_url = reverse(
            "core:zaak-detail",
            kwargs={
                "bronorganisatie": zaak.bronorganisatie,
                "identificatie": zaak.identificatie,
            },
        )
        zaak_absolute_url = self.request.build_absolute_uri(zaak_url)
        message = f"""Dear {user.get_short_name() or user.username}

The access to zaak {zaak.identificatie} is {action}.

{"you can see it here: " + zaak_absolute_url if action == 'approved' else ''}

Best regards,
ZAC Team
"""
        send_mail(
            subject=f"Access Request to {zaak.identificatie}",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[self.instance.requester.email],
        )

    def save(self, **kwargs):
        instance = super().save(**kwargs)

        # send email
        self.send_email()

        return instance
