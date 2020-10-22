import itertools
import logging
from datetime import date, datetime
from typing import Any, Dict, Iterator, List, Tuple

from django import forms
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.template.loader import get_template
from django.urls import reverse
from django.utils.html import format_html
from django.utils.http import is_safe_url
from django.utils.translation import ugettext_lazy as _

from django_camunda.api import get_process_instance_variable
from django_camunda.camunda_models import Task
from zgw_consumers.api_models.catalogi import BesluitType, ZaakType
from zgw_consumers.api_models.zaken import Zaak

from zac.accounts.constants import AccessRequestResult
from zac.accounts.models import AccessRequest, User
from zac.camunda.forms import BaseTaskFormSet, TaskFormMixin
from zac.contrib.kownsl.api import create_review_request
from zac.utils.sorting import sort

from .fields import AlfrescoDocumentField, DocumentsMultipleChoiceField
from .services import (
    get_besluittypen_for_zaaktype,
    get_documenten,
    get_resultaattypen,
    get_statustypen,
    get_zaak,
    zet_resultaat,
    zet_status,
)

logger = logging.getLogger(__name__)


def dict_to_choices(
    mapping: Dict[str, Any], attr="omschrijving"
) -> Iterator[Tuple[str, str]]:
    def choices():
        for key, value in mapping.items():
            display = getattr(value, attr)
            yield (key, display)

    return choices


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

    #TODO Update this doc string
    This is essentially the combination of :class:`SelectDocumentsForm` and
    :class:`SelectUsersForm`, which deprecates these.
    """

    template_name = "core/zaak_review_request.html"

    documenten = forms.MultipleChoiceField(
        label=_("Selecteer de relevante documenten"),
        help_text=_(
            "Dit zijn de documenten die bij de zaak horen. Selecteer de relevante "
            "documenten voor het vervolg van het proces."
        ),
        widget=forms.CheckboxSelectMultiple,
    )

    toelichting = forms.CharField(
        widget=forms.Textarea,
        required=False,
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
        return {
            "kownslDocuments": self.cleaned_data["documenten"],
        }

    def on_submission(self):
        assert self._review_type, "Subclasses must define a '_review_type'"


class SelectUsersReviewRequestForm(forms.Form):
    """
    Select a (subset of) user(s) for the review request.
    """

    kownsl_users = forms.ModelMultipleChoiceField(
        required=True,
        label=_("Users"),
        queryset=User.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple,
        help_text=_("Select the advisors."),
    )

    deadline = forms.DateField(
        required=True,
        label=_("Deadline"),
        help_text=_("Select a date"),
    )


class BaseReviewRequestFormSet(BaseTaskFormSet):
    def deadlines_validation(self) -> bool:
        """
        Validate that deadlines per step are monotonic increasing
        """
        valid = True
        deadline_old = date(1, 1, 1)
        for form in self.forms:
            deadline_new = form.cleaned_data["deadline"]
            if deadline_new and not deadline_new > deadline_old:
                form.add_error(
                    None,
                    _(
                        f"Please select a date greater than {deadline_old.strftime('%Y-%m-%d')}"
                    ),
                )
                valid = False
        return valid

    def unique_user_validation(self) -> bool:
        """
        Validate that users are unique and that at least 1 user is selected per step
        """
        valid = True
        users_list = []
        for form in self.forms:
            users = form.cleaned_data["kownsl_users"]
            if not users:
                form_add_error(None, _("Please select at least 1 advisor."))
                valid = False

            if any([user in users_list for user in users]):
                form.add_error(None, _("Please select unique advisors."))
                valid = False

            users_list.extend(users)
        return valid

    def is_valid(self) -> bool:
        valid = super().is_valid()
        # make sure deadlines are monotonic increasing and all users are unique
        return all(
            [
                valid,
                self.deadlines_validation(),
                self.unique_user_validation(),
            ]
        )

    def get_request_kownsl_user_data(self) -> List:
        """
        Grabs usernames from form
        """
        kownsl_users_list = []
        for form in self.cleaned_data:
            kownsl_users = [user.username for user in form['kownsl_users']]
            kownsl_users_list.append(kownsl_users)

        return kownsl_users_list 

    def get_process_variables(self) -> Dict[str, List]:
        assert self.is_valid(), "Formset must be valid"

        return {
            "kownslUsersList": self.get_request_kownsl_user_data(),
            "kownslReviewRequestId": str(self.review_request.id),
            "kownslFrontendUrl": self.review_request.frontend_url,
            "sendEmails": True,
        }

    def on_submission(self, form=None):
        count_users = sum(
            [
                len(users_data["kownsl_users"])
                for users_data in self.cleaned_data
                if users_data
            ]
        )

        self.review_request = create_review_request(
            form.zaak_url,
            documents=form.cleaned_data["documenten"],
            review_type=form._review_type,
            num_assigned_users=count_users,
            toelichting=form.cleaned_data["toelichting"],
        )


UsersReviewRequestFormSet = forms.formset_factory(
    SelectUsersReviewRequestForm,
    formset=BaseReviewRequestFormSet,
    extra=1,
)


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

        return super().save()


class AccessRequestHandleForm(forms.ModelForm):
    """
    Reject or approve access requests for a particular zaak
    """

    checked = forms.BooleanField(required=False)

    class Meta:
        model = AccessRequest
        fields = ("checked", "end_date")
        widgets = {"end_date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, **kwargs):
        self.request = kwargs.pop("request")

        super().__init__(**kwargs)

    def clean(self):
        super().clean()
        checked = self.cleaned_data["checked"]
        end_date = self.cleaned_data["end_date"]
        submit = self.data.get("submit")

        #  save end date only if the result == approve
        if not checked:
            return None

        if submit == AccessRequestResult.approve and not end_date:
            self.add_error("end_date", _("End date of the access must be specified"))

        return self.cleaned_data

    def send_email(self):
        user = self.instance.requester

        if not user.email:
            logger.warning("Email to %s can't be sent - no known e-mail", user)
            return

        zaak = get_zaak(zaak_url=self.instance.zaak)
        zaak_url = reverse(
            "core:zaak-detail",
            kwargs={
                "bronorganisatie": zaak.bronorganisatie,
                "identificatie": zaak.identificatie,
            },
        )
        zaak.absolute_url = self.request.build_absolute_uri(zaak_url)

        email_template = get_template("core/emails/access_request_result.txt")
        email_context = {
            "zaak": zaak,
            "access_request": self.instance,
            "user": user,
        }

        message = email_template.render(email_context)
        send_mail(
            subject=_("Access Request to %(zaak)s") % {"zaak": zaak.identificatie},
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )

    @transaction.atomic
    def save(self, **kwargs):
        checked = self.cleaned_data["checked"]

        if not checked:
            return self.instance

        self.instance.result = self.data.get("submit")
        self.instance.handler = self.request.user
        self.instance.start_date = date.today()

        instance = super().save(**kwargs)

        # send email
        transaction.on_commit(self.send_email)

        return instance


class BaseAccessRequestFormSet(forms.BaseModelFormSet):
    def clean(self):
        super().clean()

        submit = self.data.get("submit")
        if submit not in dict(AccessRequestResult.choices):
            raise forms.ValidationError(_("Use correct 'submit' button"))


class BesluitForm(forms.Form):
    besluittype = forms.TypedChoiceField(
        required=True,
        label=_("Type"),
        help_text=_(
            "Selecteer een besluittype. Deze besluittypen horen bij het zaaktype van de zaak."
        ),
    )
    beslisdatum = forms.DateField(
        label=_("Beslisdatum"),
        required=True,
        initial=date.today,
        help_text=_("De beslisdatum (AWB) van het besluit."),
    )
    ingangsdatum = forms.DateField(
        label=_("Ingangsdatum"),
        required=True,
        initial=date.today,
        help_text=_("Ingangsdatum van de werkingsperiode van het besluit."),
    )

    document = AlfrescoDocumentField(
        required=False,
        label=_("Document"),
        help_text=_("Document waarin het besluit is vastgelegd."),
    )

    def __init__(self, *args, **kwargs):
        self.zaak: Zaak = kwargs.pop("zaak")
        super().__init__(*args, **kwargs)

        self.fields["document"].zaak = self.zaak

        besluittypen = {
            besluittype.url: besluittype
            for besluittype in get_besluittypen_for_zaaktype(self.zaak.zaaktype)
        }
        self.fields["besluittype"].choices = dict_to_choices(besluittypen)
        self.fields["besluittype"].coerce = besluittypen.get

    def as_api_body(self) -> Dict[str, Any]:
        besluittype: BesluitType = self.cleaned_data["besluittype"]
        return {
            "verantwoordelijkeOrganisatie": self.zaak.bronorganisatie,
            "besluittype": besluittype.url,
            "zaak": self.zaak.url,
            "datum": self.cleaned_data["beslisdatum"].isoformat(),
            "ingangsdatum": self.cleaned_data["ingangsdatum"].isoformat(),
        }
