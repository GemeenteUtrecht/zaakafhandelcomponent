from typing import Any, Dict, List, Tuple

import tablib
from zgw_consumers.api_models.zaken import Status, Zaak
from zgw_consumers.concurrent import parallel

from zac.core.services import _get_from_catalogus, get_status, get_zaak
from zac.elasticsearch.searches import search

from .models import Report

JSONDict = Dict[str, Any]


def _get_zaaktypen(report: Report) -> List[JSONDict]:
    identificaties = report.zaaktypen

    def _get_zaaktype_versions(identificatie: str):
        return _get_from_catalogus(
            "zaaktype", catalogus="", identificatie=identificatie
        )

    with parallel() as executor:
        zaaktypen = executor.map(_get_zaaktype_versions, identificaties)

    all_zaaktypen = sum(zaaktypen, [])
    return all_zaaktypen


def get_export_zaken(report: Report) -> Tuple[Dict[str, JSONDict], List[Zaak]]:
    zaaktypen = {zaaktype["url"]: zaaktype for zaaktype in _get_zaaktypen(report)}
    zaak_urls = search(
        zaaktypen=list(zaaktypen.keys()),
        include_closed=False,
        ordering=["startdatum", "registratiedatum", "identificatie"],
    )

    with parallel() as executor:
        zaken = executor.map(lambda url: get_zaak(zaak_url=url), zaak_urls)

    return zaaktypen, list(zaken)


def export_zaken(report: Report) -> tablib.Dataset:
    zaaktypen, zaken = get_export_zaken(report)

    # get the statuses
    with parallel() as executor:
        statuses = executor.map(get_status, zaken)

    zaak_statuses: Dict[str, str] = {
        status.zaak: status.statustype.omschrijving for status in statuses if status
    }

    data = tablib.Dataset(
        headers=[
            "zaaknummer",
            "zaaktype",
            "omschrijving",
            "eigenschappen",
            "status",
        ]
    )
    for zaak in zaken:
        zaaktype = zaaktypen[zaak.zaaktype]
        data.append(
            [
                zaak.identificatie,
                zaaktype["omschrijving"],
                zaak.omschrijving,
                "",
                zaak_statuses[zaak.url] if zaak.status else "",
            ]
        )
    return data
