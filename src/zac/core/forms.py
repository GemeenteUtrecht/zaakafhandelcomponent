from django import forms
from django.template.defaultfilters import date
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from .services import get_zaaktypes


def get_zaaktype_choices():
    today = timezone.now().date()
    zaaktypen = get_zaaktypes()
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
