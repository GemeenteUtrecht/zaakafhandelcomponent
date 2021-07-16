import itertools
import logging
from datetime import date
from typing import Any, Dict, Iterator, List, Tuple

from django import forms
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from zgw_consumers.api_models.catalogi import BesluitType, ZaakType

from zac.utils.sorting import sort
from zgw.models.zrc import Zaak

from .fields import AlfrescoDocumentField
from .services import get_besluittypen_for_zaaktype

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
