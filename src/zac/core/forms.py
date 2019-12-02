from django import forms
from django.utils.translation import ugettext_lazy as _

from .services import get_zaaktypes


def get_zaaktype_choices():
    # TODO: sorting of zaaktypes
    for zaaktype in get_zaaktypes():
        yield (zaaktype.url, zaaktype.omschrijving)


class ZakenFilterForm(forms.Form):
    zaaktypen = forms.MultipleChoiceField(
        label=_("zaaktypen"),
        choices=get_zaaktype_choices,
        widget=forms.CheckboxSelectMultiple,
    )
