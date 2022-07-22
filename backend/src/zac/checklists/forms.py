from django import forms
from django.utils.translation import gettext_lazy as _

from zac.core.services import fetch_zaaktype, get_catalogi, get_zaaktypen

from .models import ChecklistType


def get_zaaktypen_choices():
    zaaktypen = get_zaaktypen()
    zaaktypen = sorted(
        sorted(zaaktypen, key=lambda _zt: _zt.versiedatum, reverse=True),
        key=lambda zt: (zt.omschrijving,),
    )
    catalogi = {cat.url: cat.domein for cat in get_catalogi()}

    return (
        (
            zt.url,
            f"{catalogi[zt.catalogus]} - {zt.omschrijving} - {zt.identificatie}: {zt.versiedatum}",
        )
        for zt in zaaktypen
    )


class ChecklistTypeForm(forms.ModelForm):
    zaaktype = forms.ChoiceField(choices=get_zaaktypen_choices)
    zaaktype_catalogus = forms.URLField(
        label=_("Catalogus"),
        max_length=1000,
        help_text=_(
            "URL-reference to CATALOGUS of ZAAKTYPE. A selected ZAAKTYPE will update this value."
        ),
        required=False,
        disabled=True,
    )
    zaaktype_identificatie = forms.CharField(
        label=_("Identificatie"),
        max_length=80,
        help_text=_(
            "`identificatie` of ZAAKTYPE. A selected ZAAKTYPE will update this value."
        ),
        required=False,
        disabled=True,
    )

    class Meta:
        model = ChecklistType
        fields = ("zaaktype",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.initial:
            self.fields["zaaktype"].initial = sorted(
                get_zaaktypen(
                    catalogus=self.initial["zaaktype_catalogus"],
                    identificatie=self.initial["zaaktype_identificatie"],
                ),
                key=lambda zt: zt.versiedatum,
                reverse=True,
            )[0].url

    def clean(self):
        super().clean()
        if zt_url := self.cleaned_data.get("zaaktype"):
            zt = fetch_zaaktype(zt_url)
            self.cleaned_data["zaaktype_identificatie"] = zt.identificatie
            self.cleaned_data["zaaktype_catalogus"] = zt.catalogus
