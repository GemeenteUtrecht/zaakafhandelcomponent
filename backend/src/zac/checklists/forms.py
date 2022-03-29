from django import forms
from django.utils.translation import gettext_lazy as _

from zac.core.services import fetch_zaaktype, get_zaaktypen

from .models import ChecklistType


def get_zaaktypen_choices():
    zaaktypen = get_zaaktypen()
    zaaktypen = sorted(
        sorted(zaaktypen, key=lambda _zt: _zt.versiedatum, reverse=True),
        key=lambda zt: (zt.omschrijving,),
    )
    return (
        (zt.url, f"{zt.omschrijving} {zt.versiedatum} {zt.catalogus}")
        for zt in zaaktypen
    )


class ChecklistTypeForm(forms.ModelForm):
    zaaktype = forms.ChoiceField(choices=get_zaaktypen_choices)
    zaaktype_catalogus = forms.URLField(
        label=_("Catalogus"),
        max_length=1000,
        help_text=_(
            "URL-referentie naar de CATALOGUS van het ZAAKTYPE. Een geselecteerd ZAAKTYPE zal deze waarde overschrijven."
        ),
        required=False,
        disabled=True,
    )
    zaaktype_omschrijving = forms.CharField(
        label=_("Omschrijving"),
        max_length=80,
        help_text=_(
            "Omschrijving van het ZAAKTYPE. Een geselecteerd ZAAKTYPE zal deze waarde overschrijven."
        ),
        required=False,
        disabled=True,
    )

    class Meta:
        model = ChecklistType
        fields = ("zaaktype",)

    def clean(self):
        super().clean()
        if zt_url := self.cleaned_data.get("zaaktype"):
            zt = fetch_zaaktype(zt_url)
            self.cleaned_data["zaaktype_omschrijving"] = zt.omschrijving
            self.cleaned_data["zaaktype_catalogus"] = zt.catalogus
