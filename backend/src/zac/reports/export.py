from typing import Dict, Iterator, List, Tuple

import tablib
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.api_models.zaken import Status, ZaakEigenschap
from zgw_consumers.concurrent import parallel

from zac.accounts.models import User
from zac.core.services import (
    _get_from_catalogus,
    get_status,
    get_zaak,
    get_zaak_eigenschappen,
)
from zac.elasticsearch.searches import search
from zgw.models.zrc import Zaak

from .models import Report


def _get_zaaktypen(report: Report) -> List[ZaakType]:
    identificaties = report.zaaktypen

    with parallel() as executor:
        zaaktypen = executor.map(
            lambda identificatie: _get_from_catalogus(
                "zaaktype", catalogus="", identificatie=identificatie
            ),
            identificaties,
        )

    all_zaaktypen = sum(zaaktypen, [])
    return factory(ZaakType, all_zaaktypen)


def get_export_zaken(user: User, report: Report, ordering: List[str]) -> List[Zaak]:
    zaaktypen = {zaaktype.url: zaaktype for zaaktype in _get_zaaktypen(report)}
    zaak_urls = search(
        user=user,
        zaaktypen=list(zaaktypen.keys()),
        include_closed=False,
        ordering=ordering,
    )

    with parallel() as executor:
        zaken = executor.map(lambda url: get_zaak(zaak_url=url), zaak_urls)

    zaken = list(zaken)
    for zaak in zaken:
        zaak.zaaktype = zaaktypen[zaak.zaaktype]

    return zaken


def get_zaken_details_for_export(
    user: User,
    report: Report,
    ordering: List[str] = ["startdatum", "registratiedatum", "identificatie"],
) -> Tuple[List[Zaak], Dict[str, str], Dict[str, List[ZaakEigenschap]]]:
    zaken = get_export_zaken(user, report, ordering=ordering)

    # get the statuses & eigenschappen
    with parallel() as executor:
        statuses: Iterator[Status] = executor.map(get_status, zaken)
        eigenschappen: Iterator[List[ZaakEigenschap]] = executor.map(
            get_zaak_eigenschappen, zaken
        )

    zaak_statuses = {
        status.zaak: status.statustype.omschrijving for status in statuses if status
    }
    zaak_eigenschappen = {
        zaak_eigenschappen[0].zaak.url: zaak_eigenschappen
        for zaak_eigenschappen in eigenschappen
        if zaak_eigenschappen
    }
    return zaken, zaak_statuses, zaak_eigenschappen


def export_zaken_as_tablib_dataset(user: User, report: Report) -> tablib.Dataset:
    zaken, zaak_statuses, zaak_eigenschappen = get_zaken_details_for_export(
        user, report
    )

    data = tablib.Dataset(
        headers=[
            "zaaknummer",
            "zaaktype",
            "startdatum",
            "omschrijving",
            "eigenschappen",
            "status",
        ]
    )
    for zaak in zaken:
        eigenschappen = zaak_eigenschappen.get(zaak.url) or ""
        if eigenschappen:
            formatted = [
                f"{eigenschap.naam}: {eigenschap.waarde}"
                for eigenschap in sorted(eigenschappen, key=lambda e: e.naam)
            ]
            eigenschappen = "\n".join(formatted)

        data.append(
            [
                zaak.identificatie,
                zaak.zaaktype.omschrijving,
                zaak.startdatum,
                zaak.omschrijving,
                eigenschappen,
                zaak_statuses[zaak.url] if zaak.status else "",
            ]
        )
    return data
