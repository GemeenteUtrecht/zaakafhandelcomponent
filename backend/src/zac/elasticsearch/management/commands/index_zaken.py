import logging
from typing import Dict, Iterator, List

from django.conf import settings
from django.core.management import BaseCommand

from zgw_consumers.concurrent import parallel
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from zac.core.services import (
    fetch_zaaktype,
    get_rollen,
    get_status,
    get_zaakeigenschappen,
    get_zaaktypen,
    get_zaken_all_paginated,
)
from zgw.models import Zaak

from ...api import (
    create_eigenschappen_document,
    create_rol_document,
    create_status_document,
    create_zaak_document,
    create_zaaktype_document,
)
from ...documents import (
    EigenschapDocument,
    RolDocument,
    StatusDocument,
    ZaakDocument,
    ZaakTypeDocument,
)
from ..utils import get_memory_usage
from .base_index import IndexCommand

perf_logger = logging.getLogger("performance")


class Command(IndexCommand, BaseCommand):
    help = "Create documents in ES by indexing all ZAAKen from ZAKEN API."
    _index = settings.ES_INDEX_ZAKEN
    _type = "zaak"
    _document = ZaakDocument
    _verbose_name_plural = "ZAAKen"

    def batch_index(self) -> Iterator[ZaakDocument]:
        super().batch_index()
        self.stdout.write("Preloading all ZAAKTYPEn...")
        zaaktypen = {zt.url: zt for zt in get_zaaktypen()}
        self.stdout.write(f"Fetched {len(zaaktypen)} ZAAKTYPEn.")

        if self.reindex_zaak:
            zaak = self.get_reindexable_zaak()
            zaak.zaaktype = zaaktypen[zaak.zaaktype]
            yield from self.documenten_generator([zaak])

        else:
            self.stdout.write(
                f"Starting {self.verbose_name_plural} retrieval from the configured APIs."
            )

            zrcs = Service.objects.filter(api_type=APITypes.zrc)
            clients = [zrc.build_client() for zrc in zrcs]

            # report back which clients will be iterated over and how many zaken each has
            total_expected_zaken = 0
            for client in clients:
                # fetch the first page so we get the total count from the backend
                response = client.list("zaak", headers={"Accept-Crs": "EPSG:4326"})
                client_num_zaken = response["count"]
                total_expected_zaken += client_num_zaken
                self.stdout.write(
                    f"Number of ZAAKen in {client.base_url}:\n  {client_num_zaken}."
                )

            if self.reindex_last:
                total_expected_zaken = min(total_expected_zaken, self.reindex_last)
                self.reindexed = 0

            self.stdout.write("Now the real work starts, hold on!")

            self.stdout.start_progress()

            for client in clients:
                perf_logger.info("Starting indexing for client %s.", client)
                perf_logger.info("Memory usage: %s.", get_memory_usage())
                get_more = True
                # Set ordering explicitely
                query_params = {"ordering": "-identificatie"}
                while get_more:
                    # if this is running for 1h+, Open Zaak expires the token
                    client.refresh_auth()
                    perf_logger.info(
                        "Fetching ZAAKen for client, query params: %r.", query_params
                    )
                    zaken, query_params = get_zaken_all_paginated(
                        client, query_params=query_params
                    )
                    perf_logger.info("Fetched %d ZAAKen.", len(zaken))
                    # Make sure we're not retrieving more information than necessary on the zaken
                    if self.reindex_last and self.reindex_last - self.reindexed <= len(
                        zaken
                    ):
                        zaken = zaken[: self.reindex_last - self.reindexed]

                    get_more = query_params.get("page", None)
                    for zaak in zaken:
                        zaak.zaaktype = zaaktypen[zaak.zaaktype]

                    perf_logger.info("Entering ES documents generator.")
                    perf_logger.info("Memory usage: %s.", get_memory_usage())
                    yield from self.documenten_generator(zaken)
                    perf_logger.info("Exited ES documents generator.")

            self.stdout.end_progress()

    def documenten_generator(self, zaken: List[Zaak]) -> Iterator[ZaakDocument]:
        perf_logger.info("  In ES documents generator.")
        perf_logger.info("    Create ZAAK documents...")
        zaak_documenten = self.create_zaak_documenten(zaken)
        perf_logger.info("    Create ZAAK documents finished.")
        perf_logger.info("    Create ZAAKTYPE documents...")
        zaaktype_documenten = self.create_zaaktype_documenten(zaken)
        perf_logger.info("    Create ZAAKTYPE documents finished.")
        perf_logger.info("    Create STATUS documents...")
        status_documenten = self.create_status_documenten(zaken)
        perf_logger.info("    Create STATUS documents finished.")
        perf_logger.info("    Create ROL documents...")
        rollen_documenten = self.create_rollen_documenten(zaken)
        perf_logger.info("    Create ROL documents finished.")
        perf_logger.info("    Create EIGENSCHAP documents...")
        eigenschappen_documenten = self.create_eigenschappen_documenten(zaken)
        perf_logger.info("    Create EIGENSCHAP documents finished.")
        perf_logger.info("    Relating all results for every ZAAK...")
        for zaak in zaken:
            zaakdocument = zaak_documenten[zaak.url]
            zaakdocument.zaaktype = zaaktype_documenten[zaak.url]
            zaakdocument.status = status_documenten.get(zaak.url, None)
            zaakdocument.rollen = rollen_documenten.get(zaak.url, [])
            zaakdocument.eigenschappen = eigenschappen_documenten.get(zaak.url, {})
            zd = zaakdocument.to_dict(True)
            yield zd
            if self.reindex_last:
                self.reindexed += 1

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
        self.stdout.write_without_progress(
            f"{len(status_documenten.keys())} STATUSsen are received from ZAKEN API."
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

        num_roles = sum([len(rollen) for rollen in list_of_rollen])
        self.stdout.write_without_progress(
            f"{num_roles} ROLlen are received for {len(rollen_documenten.keys())} ZAAKen."
        )
        return rollen_documenten

    def create_eigenschappen_documenten(
        self, zaken: List[Zaak]
    ) -> Dict[str, EigenschapDocument]:
        # Prefetch zaakeigenschappen
        with parallel(max_workers=self.max_workers) as executor:
            list_of_eigenschappen = list(executor.map(get_zaakeigenschappen, zaken))

        eigenschappen_documenten = {
            zen[0].zaak: create_eigenschappen_document(zen)
            for zen in list_of_eigenschappen
            if zen
        }

        num_properties = sum([len(zen) for zen in list_of_eigenschappen])
        self.stdout.write_without_progress(
            f"{num_properties} ZAAKEIGENSCHAPpen are found for {len(eigenschappen_documenten.keys())} ZAAKen."
        )
        return eigenschappen_documenten
