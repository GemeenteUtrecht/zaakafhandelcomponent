from typing import Dict, Iterator, List

from django.conf import settings
from django.core.management import BaseCommand
from django.core.management.base import CommandParser

from elasticsearch.helpers import bulk
from elasticsearch_dsl import Index
from elasticsearch_dsl.connections import connections
from zgw_consumers.concurrent import parallel
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from zac.core.services import (
    fetch_zaaktype,
    get_rollen,
    get_status,
    get_zaak_eigenschappen,
    get_zaakobjecten,
    get_zaaktypen,
    get_zaken_all_paginated,
)
from zgw.models import Zaak

from ...api import (
    create_eigenschappen_document,
    create_rol_document,
    create_status_document,
    create_zaak_document,
    create_zaakobject_document,
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

    def add_arguments(self, parser: CommandParser) -> None:
        super().add_arguments(parser)
        parser.add_argument(
            "--max_workers",
            type=int,
            help="Indicates the max number of parallel workers (for memory management). Defaults to 4.",
            default=4,
        )

    def handle(self, **options):
        self.max_workers = options["max_workers"]
        self.clear_zaken_index()
        bulk(
            connections.get_connection(),
            self.batch_index_zaken(),
        )

        count = ZaakDocument.search().count()
        self.stdout.write(f"{count} zaken are received from Zaken API.")

    def batch_index_zaken(self) -> Iterator[ZaakDocument]:
        ZaakDocument.init()
        zaaktypen = {zt.url: zt for zt in get_zaaktypen()}

        zrcs = Service.objects.filter(api_type=APITypes.zrc)
        clients = [zrc.build_client() for zrc in zrcs]
        for client in clients:
            get_more = True
            query_params = {}
            while get_more:
                zaken, query_params = get_zaken_all_paginated(
                    client, query_params=query_params
                )
                get_more = query_params.get("page", None)
                for zaak in zaken:
                    zaak.zaaktype = zaaktypen[zaak.zaaktype]

                yield from self.zaakdocumenten_generator(zaken)

    def zaakdocumenten_generator(self, zaken: List[Zaak]) -> Iterator[ZaakDocument]:
        zaak_documenten = self.create_zaak_documenten(zaken)
        zaaktype_documenten = self.create_zaaktype_documenten(zaken)
        status_documenten = self.create_status_documenten(zaken)
        rollen_documenten = self.create_rollen_documenten(zaken)
        eigenschappen_documenten = self.create_eigenschappen_documenten(zaken)
        zaakobjecten_documenten = self.create_zaakobject_documenten(zaken)

        for zaak in zaken:
            zaakdocument = zaak_documenten[zaak.url]
            zaakdocument.zaaktype = zaaktype_documenten[zaak.url]
            zaakdocument.status = status_documenten.get(zaak.url, None)
            zaakdocument.rollen = rollen_documenten.get(zaak.url, [])
            zaakdocument.eigenschappen = eigenschappen_documenten.get(zaak.url, {})
            zaakdocument.zaakobjecten = zaakobjecten_documenten.get(zaak.url, [])
            zd = zaakdocument.to_dict(True)
            yield zd

    def clear_zaken_index(self):
        zaken = Index(settings.ES_INDEX_ZAKEN)
        zaken.delete(ignore=404)

    def create_zaak_documenten(self, zaken: List[Zaak]) -> Dict[str, ZaakDocument]:
        # Build the zaak_documenten
        zaak_documenten = {zaak.url: create_zaak_document(zaak) for zaak in zaken}
        return zaak_documenten

    def create_zaaktype_documenten(
        self, zaken: List[Zaak]
    ) -> Dict[str, ZaakTypeDocument]:
        unfetched_zaaktypen = {
            zaak.zaaktype for zaak in zaken if isinstance(zaak.zaaktype, str)
        }
        with parallel(max_workers=self.max_workers) as executor:
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
        with parallel(max_workers=self.max_workers) as executor:
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

    def create_rollen_documenten(self, zaken: List[Zaak]) -> Dict[str, RolDocument]:
        with parallel(max_workers=self.max_workers) as executor:
            results = list(executor.map(get_rollen, zaken))

        list_of_rollen = [rollen for rollen in results if rollen]

        rollen_documenten = {
            rollen[0].zaak: [create_rol_document(rol) for rol in rollen]
            for rollen in list_of_rollen
        }
        self.stdout.write(
            f"{sum([len(rollen) for rollen in list_of_rollen])} rollen are received for {len(rollen_documenten.keys())} zaken."
        )
        return rollen_documenten

    def create_eigenschappen_documenten(
        self, zaken: List[Zaak]
    ) -> Dict[str, EigenschapDocument]:
        # Prefetch zaakeigenschappen
        with parallel(max_workers=self.max_workers) as executor:
            list_of_eigenschappen = list(executor.map(get_zaak_eigenschappen, zaken))

        eigenschappen_documenten = {
            zen[0].zaak: create_eigenschappen_document(zen)
            for zen in list_of_eigenschappen
            if zen
        }
        self.stdout.write(
            f"{sum([len(zen) for zen in list_of_eigenschappen])} zaakeigenschappen are found for {len(eigenschappen_documenten.keys())} zaken."
        )
        return eigenschappen_documenten

    def create_zaakobject_documenten(
        self, zaken: List[Zaak]
    ) -> Dict[str, ZaakObjectDocument]:
        # Prefetch zaakobjecten
        with parallel(max_workers=self.max_workers) as executor:
            list_of_zon = list(executor.map(get_zaakobjecten, zaken))

        zaakobjecten_documenten = {
            zon[0].zaak: [create_zaakobject_document(zo) for zo in zon]
            for zon in list_of_zon
            if zon
        }
        self.stdout.write(
            f"{sum([len(zon) for zon in list_of_zon])} zaakobjecten are found for {len(zaakobjecten_documenten.keys())} zaken."
        )
        return zaakobjecten_documenten
