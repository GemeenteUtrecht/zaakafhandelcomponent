from itertools import groupby
from typing import List, Tuple

from django import forms
from django.utils.translation import gettext_lazy as _

from django_camunda.client import get_client

from zac.core.services import fetch_zaaktype, get_catalogi, get_zaaktypen

from .models import CamundaStartProcess


def get_zaaktypen_choices() -> Tuple[Tuple[str, str]]:
    zaaktypen = get_zaaktypen()
    catalogi = {cat.url: cat for cat in get_catalogi()}
    for zt in zaaktypen:
        zt.catalogus = catalogi[zt.catalogus]

    zaaktypen = sorted(
        sorted(
            sorted(zaaktypen, key=lambda zt: zt.versiedatum, reverse=True),
            key=lambda zt: zt.catalogus.domein,
        ),
        key=lambda zt: (zt.omschrijving, zt.identificatie),
    )
    zten = []
    for key, group_cat in groupby(zaaktypen, lambda zt: zt.catalogus.domein):
        for key, group_id in groupby(group_cat, lambda zt: zt.identificatie):
            group = list(group_id)
            max_date = max([zt.versiedatum for zt in group])
            zten += [zt for zt in group if zt.versiedatum == max_date]

    return (
        (
            zt.url,
            f"{zt.omschrijving} - {zt.catalogus.domein} - {zt.identificatie} - {zt.versiedatum}",
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["zaaktype"].initial = self.instance.zaaktype.url

    def clean(self):
        super().clean()
        if zt_url := self.cleaned_data.get("zaaktype"):
            zt = fetch_zaaktype(zt_url)
            self.cleaned_data["zaaktype_identificatie"] = zt.identificatie
            self.cleaned_data["zaaktype_catalogus"] = zt.catalogus
