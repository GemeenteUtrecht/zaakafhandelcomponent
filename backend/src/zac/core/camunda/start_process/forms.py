from itertools import groupby
from typing import List, Tuple

from django import forms
from django.utils.translation import gettext_lazy as _

from django_camunda.client import get_client

from zac.core.services import fetch_zaaktype, get_zaaktypen

from .models import CamundaStartProcess


def get_zaaktypen_choices() -> Tuple[Tuple[str, str]]:
    zaaktypen = get_zaaktypen()
    zaaktypen = sorted(
        sorted(zaaktypen, key=lambda _zt: _zt.versiedatum, reverse=True),
        key=lambda zt: (zt.omschrijving, zt.identificatie),
    )
    zten = []
    for key, group in groupby(zaaktypen, lambda zt: zt.identificatie):
        group = list(group)
        max_date = max([zt.versiedatum for zt in group])
        zten += [zt for zt in group if zt.versiedatum == max_date]

    return (
        (
            zt.url,
            f"{zt.omschrijving} Identificatie: {zt.identificatie} Versiedatum: {zt.versiedatum}",
        )
        for zt in zten
    )


def get_process_definition_keys() -> List[str]:
    camunda_client = get_client()
    process_definitions = camunda_client.get("process-definition?latestVersion=true")
    return ((pdef["name"], pdef["key"]) for pdef in process_definitions)


class CamundaStartProcessForm(forms.ModelForm):
    process_definition_key = forms.ChoiceField(choices=get_process_definition_keys)
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
    zaaktype_identificatie = forms.CharField(
        label=_("Identificatie"),
        max_length=80,
        help_text=_(
            "`identificatie` van het ZAAKTYPE. Een geselecteerd ZAAKTYPE zal deze waarde overschrijven."
        ),
        required=False,
        disabled=True,
    )

    class Meta:
        model = CamundaStartProcess
        fields = ("zaaktype",)

    def clean(self):
        super().clean()
        if zt_url := self.cleaned_data.get("zaaktype"):
            zt = fetch_zaaktype(zt_url)
            self.cleaned_data["zaaktype_identificatie"] = zt.identificatie
            self.cleaned_data["zaaktype_catalogus"] = zt.catalogus
