import logging
from typing import Dict, List

from django.conf import settings
from django.core.management import BaseCommand

from elasticsearch.helpers import bulk
from elasticsearch_dsl import Index
from elasticsearch_dsl.connections import connections
from zgw_consumers.concurrent import parallel

from zac.core.services import (
    fetch_zaaktype,
    get_rollen_all,
    get_status,
    get_zaak_eigenschappen,
    get_zaakobjecten,
    get_zaken_all,
)
from zgw.models import Zaak

from ...api import (
    create_eigenschappen_document,
    create_rol_document,
    create_status_document,
    create_zaak_document,
    create_zaakobjecten_document,
    create_zaaktype_document,
)
from ...documents import (
    EigenschapDocument,
    RolDocument,
    StatusDocument,
    ZaakDocument,
    ZaakObjectDocument,
    ZaakTypeDocument,
)


class Command(BaseCommand):
    help = "Create documents in ES by indexing all zaken from ZAKEN API"

    def handle(self, **options):
        self.clear_zaken_index()

        zaken = get_zaken_all()
        self.stdout.write(f"{len(zaken)} zaken are received from Zaken API.")

        zaak_documenten = self.create_zaak_documenten(zaken)
        zaaktype_documenten = self.create_zaaktype_documenten(zaken)
        status_documenten = self.create_status_documenten(zaken)
        rollen_documenten = self.create_rollen_documenten()
        eigenschappen_documenten = self.create_eigenschappen_documenten(zaken)
        zaakobjecten_documenten = self.create_zaakobjecten_documenten(zaken)

        final = []
        for zaak in zaken:
            zaakdocument = zaak_documenten[zaak.url]
            zaakdocument.zaaktype = zaaktype_documenten[zaak.url]
            zaakdocument.status = status_documenten.get(zaak.url, None)
            zaakdocument.rollen = rollen_documenten.get(zaak.url, [])
            zaakdocument.eigenschappen = eigenschappen_documenten.get(zaak.url, {})
            zaakdocument.zaakobjecten = zaakobjecten_documenten.get(zaak.url, [])
            final.append(zaakdocument.to_dict(True))

        bulk(connections.get_connection(), final)
        self.stdout.write(f"All zaken have been indexed.")

    def clear_zaken_index(self):
        zaken = Index(settings.ES_INDEX_ZAKEN)
        zaken.delete(ignore=404)

    def create_zaak_documenten(self, zaken: List[Zaak]) -> Dict[str, ZaakDocument]:
        ZaakDocument.init()

        # Build the zaak_documenten
        zaak_documenten = {zaak.url: create_zaak_document(zaak) for zaak in zaken}
        return zaak_documenten

    def create_zaaktype_documenten(
        self, zaken: List[Zaak]
    ) -> Dict[str, ZaakTypeDocument]:
        unfetched_zaaktypen = {
            zaak.zaaktype for zaak in zaken if isinstance(zaak.zaaktype, str)
        }
        with parallel(max_workers=10) as executor:
            results = executor.map(fetch_zaaktype, unfetched_zaaktypen)
        zaaktypen = {zaaktype.url: zaaktype for zaaktype in list(results)}

        for zaak in zaken:
            if isinstance(zaak.zaaktype, str):
                zaak.zaaktype = zaaktypen[zaak.zaaktype]

        zaaktype_documenten = {
            zaak.url: create_zaaktype_document(zaak.zaaktype) for zaak in zaken
        }
        return zaaktype_documenten

    def create_status_documenten(self, zaken: List[Zaak]) -> Dict[str, StatusDocument]:
        with parallel(max_workers=10) as executor:
            results = executor.map(get_status, zaken)
        status_documenten = {
            status.zaak: create_status_document(status)
            for status in list(results)
            if status
        }
        self.stdout.write(
            f"{len(status_documenten.keys())} statussen are received from Zaken API."
        )
        return status_documenten

    def create_rollen_documenten(self) -> Dict[str, RolDocument]:
        rollen = get_rollen_all()
        rollen_documenten = {rol.zaak: [] for rol in rollen}

        for rol in rollen:
            rollen_documenten[rol.zaak].append(create_rol_document(rol))
        self.stdout.write(
            f"{len(rollen)} rollen are received for {len(rollen_documenten.keys())} zaken."
        )
        return rollen_documenten

    def create_eigenschappen_documenten(
        self, zaken: List[Zaak]
    ) -> Dict[str, EigenschapDocument]:
        # Prefetch zaakeigenschappen
        with parallel(max_workers=10) as executor:
            results = executor.map(get_zaak_eigenschappen, zaken)
        list_of_eigenschappen = list(results)

        eigenschappen_documenten = {
            zen[0].zaak.url: create_eigenschappen_document(zen)
            for zen in list_of_eigenschappen
            if zen
        }
        self.stdout.write(
            f"{sum([len(zen) for zen in list_of_eigenschappen])} zaakeigenschappen are found for {len(eigenschappen_documenten.keys())} zaken."
        )
        return eigenschappen_documenten

    def create_zaakobjecten_documenten(
        self, zaken: List[Zaak]
    ) -> Dict[str, ZaakObjectDocument]:
        # Prefetch zaakobjecten
        with parallel(max_workers=10) as executor:
            results = executor.map(get_zaakobjecten, zaken)
        list_of_zon = list(results)
        zaakobjecten_documenten = {
            zon[0].zaak: create_zaakobjecten_document(zon) for zon in list_of_zon if zon
        }
        self.stdout.write(
            f"{sum([len(zon) for zon in list_of_zon])} zaakobjecten are found for {len(zaakobjecten_documenten.keys())} zaken."
        )
        return zaakobjecten_documenten
