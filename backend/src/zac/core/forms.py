import itertools
import logging
from datetime import date, datetime
from typing import Any, Dict, Iterator, List, Tuple

from django import forms
from django.conf import settings
from django.db import transaction
from django.urls import reverse
from django.utils.html import format_html
from django.utils.http import is_safe_url
from django.utils.timezone import make_aware
from django.utils.translation import ugettext_lazy as _

from django_camunda.api import get_process_instance_variable
from django_camunda.camunda_models import Task
from zgw_consumers.api_models.catalogi import BesluitType, ZaakType

from zac.accounts.constants import AccessRequestResult, PermissionObjectType
from zac.accounts.email import send_email_to_requester
from zac.accounts.models import AccessRequest, AtomicPermission, User
from zac.accounts.permission_loaders import add_permissions_for_advisors
from zac.camunda.forms import BaseTaskFormSet, TaskFormMixin
from zac.contrib.kownsl.api import create_review_request
from zac.utils.sorting import sort
from zgw.models.zrc import Zaak

from .fields import AlfrescoDocumentField, DocumentsMultipleChoiceField
from .permissions import zaken_inzien
from .services import (
    get_besluittypen_for_zaaktype,
    get_documenten,
    get_resultaattypen,
    get_statustypen,
    get_zaak,
    zet_resultaat,
    zet_status,
)
from .utils import get_ui_url

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

    def get_review_type(self):
        return "Adviseur(s)" if self._review_type == "advice" else "Accordeur(s)"


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
        input_formats=["%Y-%m-%d"],
    )


class BaseReviewRequestFormSet(BaseTaskFormSet):
    def deadlines_validation(self) -> bool:
        """
        Validate that deadlines per step are monotonic increasing
        """
        deadline_old = date.today()
        errors = []
        for form in self.forms:
            deadline_new = form.cleaned_data["deadline"]
            if deadline_new and not deadline_new > deadline_old:
                errors.append(
                    forms.ValidationError(
                        _(
                            "Deadlines are not allowed to be equal in a serial review request process but need to have at least 1 day in between them. Please select a date greater than {minimum_date}."
                        ).format(minimum_date=deadline_old.strftime("%Y-%m-%d")),
                        code="date-not-valid",
                    )
                )
            deadline_old = deadline_new
        return errors

    def unique_user_validation(self) -> bool:
        """
        Validate that users are unique and that at least 1 user is selected per step
        """
        users_list = []
        errors = []
        for form in self.forms:
            users = form.cleaned_data["kownsl_users"]
            if not users:
                errors.append(
                    forms.ValidationError(
                        _("Please select at least 1 user."),
                        code="empty-user",
                    )
                )

            if any([user in users_list for user in users]):
                errors.append(
                    forms.ValidationError(
                        _(
                            "Users in a serial review request process need to be unique. Please select unique users."
                        ),
                        code="unique-user",
                    )
                )

            users_list.extend(users)
        return errors

    def clean(self):
        super().clean()
        errors = self.deadlines_validation()
        errors.extend(self.unique_user_validation())
        if errors:
            raise forms.ValidationError(errors)

    def get_request_kownsl_user_data(self) -> List:
        """
        Grabs usernames from form
        """
        kownsl_users_list = []
        for form in self.cleaned_data:
            kownsl_users = [user.username for user in form["kownsl_users"]]
            kownsl_users_list.append(kownsl_users)

        return kownsl_users_list

    def get_process_variables(self) -> Dict[str, List]:
        assert self.is_valid(), "Formset must be valid"

        kownsl_frontend_url = get_ui_url(
            [
                "ui",
                "kownsl",
                "review-request",
                self.review_request.review_type,
            ],
            params={"uuid": self.review_request.id},
        )
        return {
            "kownslUsersList": self.get_request_kownsl_user_data(),
            "kownslReviewRequestId": str(self.review_request.id),
            "kownslFrontendUrl": kownsl_frontend_url,
        }

    def get_user_deadlines(self) -> Dict:
        """
        Grabs user emails and their deadlines from form.
        This is used for sending (reminder) emails.
        """
        user_deadlines = {}
        for form in self.cleaned_data:
            deadline = form["deadline"]
            for user in form["kownsl_users"]:
                user_deadlines[user.username] = str(deadline)
        return user_deadlines

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
            user_deadlines=self.get_user_deadlines(),
            requester=self.user.username,
        )
        add_permissions_for_advisors(self.review_request)


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

    @transaction.atomic
    def save(self, **kwargs):
        checked = self.cleaned_data["checked"]

        if not checked:
            return self.instance

        self.instance.result = self.data.get("submit")
        self.instance.handler = self.request.user
        self.instance.start_date = date.today()

        instance = super().save(**kwargs)

        if self.instance.result == AccessRequestResult.approve:
            atomic_permission = AtomicPermission.objects.create(
                permission=zaken_inzien.name,
                object_type=PermissionObjectType.zaak,
                object_url=self.instance.zaak,
                start_date=make_aware(
                    datetime.combine(self.instance.start_date, datetime.min.time())
                ),
                end_date=make_aware(
                    datetime.combine(self.instance.end_date, datetime.min.time())
                )
                if self.instance.end_date
                else None,
            )
            self.instance.requester.atomic_permissions.add(atomic_permission)

        # send email
        transaction.on_commit(
            lambda: send_email_to_requester(self.instance, self.request)
        )

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
