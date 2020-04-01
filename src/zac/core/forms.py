from django import forms
from django.conf import settings
from django.template.defaultfilters import date
from django.utils import timezone
from django.utils.http import is_safe_url
from django.utils.translation import ugettext_lazy as _

from .services import get_resultaattypen, get_zaaktypen


def get_zaaktype_choices():
    today = timezone.now().date()
    zaaktypen = get_zaaktypen()
    for zaaktype in zaaktypen:
        if zaaktype.begin_geldigheid > today:
            continue

        if zaaktype.einde_geldigheid and zaaktype.einde_geldigheid < today:
            continue

        label = f"{zaaktype.omschrijving} (versie {date(zaaktype.versiedatum)})"
        yield (zaaktype.url, label)


class ZakenFilterForm(forms.Form):
    identificatie = forms.CharField(label=_("identificatie"), required=False,)
    bronorganisatie = forms.CharField(label=_("bronorganisatie"), required=False,)
    zaaktypen = forms.MultipleChoiceField(
        label=_("zaaktypen (huidige versies)"),
        required=False,
        choices=get_zaaktype_choices,
        widget=forms.CheckboxSelectMultiple,
    )

    def as_filters(self) -> dict:
        assert self.cleaned_data
        zaaktypen = self.cleaned_data.get("zaaktypen")
        identificatie = self.cleaned_data.get("identificatie")
        bronorganisatie = self.cleaned_data.get("bronorganisatie")

        filters = {}
        if zaaktypen:
            filters["zaaktypen"] = zaaktypen
        if bronorganisatie:
            filters["bronorganisatie"] = bronorganisatie
        if identificatie:
            filters["identificatie"] = identificatie

        return filters


class ClaimTaskForm(forms.Form):
    task_id = forms.CharField(required=True)
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


class ZaakAfhandelForm(forms.Form):
    resultaattype = forms.ChoiceField(
        required=False, label="Resultaat", widget=forms.RadioSelect,
    )
    result_remarks = forms.CharField(
        required=False, label="Toelichting", widget=forms.Textarea,
    )
    close_zaak = forms.BooleanField(
        required=False,
        label="Zaak afsluiten?",
        help_text="Sluit de zaak af als er een resultaat gezet is.",
    )
    close_zaak_remarks = forms.CharField(
        required=False, label="Toelichting bij afsluiten zaak", widget=forms.Textarea,
    )

    def __init__(self, *args, **kwargs):
        self.zaak = kwargs.pop("zaak")
        super().__init__(*args, **kwargs)

        # fetch the possible result types
        zaaktype = self.zaak.zaaktype

        resultaattype_choices = [
            (resultaattype.url, resultaattype.omschrijving)
            for resultaattype in get_resultaattypen(zaaktype)
        ]
        self.fields["resultaattype"].choices = resultaattype_choices

    def save(self, user):
        import bpdb

        bpdb.set_trace()
