import logging
from typing import Iterator, List

from django.conf import settings
from django.core.management import BaseCommand

from zgw_consumers.concurrent import parallel
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from zac.core.services import get_zaak_informatieobjecten, get_zaken_all_paginated
from zgw.models import Zaak

from ...api import create_zaakinformatieobject_document
from ...documents import ZaakDocument, ZaakInformatieObjectDocument
from ..utils import get_memory_usage

perf_logger = logging.getLogger("performance")

from .base_index import IndexCommand


class Command(IndexCommand, BaseCommand):
    help = "Create ZAAKINFORMATIE documents in ES by indexing all zaken from ZAKEN API."
    _index = settings.ES_INDEX_ZIO
    _type = "ZAAKINFORMATIEOBJECTen"
    _document = ZaakInformatieObjectDocument
    _verbose_name_plural = "ZAAKINFORMATIEOBJECTen"
    relies_on = {
        settings.ES_INDEX_ZAKEN: ZaakDocument,
    }

    def batch_index(self) -> Iterator[ZaakInformatieObjectDocument]:
        super().batch_index()
        zaken = self.get_zaken()
        self.stdout.write(
            f"Starting {self.verbose_name_plural} retrieval from the configured APIs."
        )

        if not zaken:
            zrcs = Service.objects.filter(api_type=APITypes.zrc)
            clients = [zrc.build_client() for zrc in zrcs]

            # report back which clients will be iterated over and how many zaken each has
            total_expected_zaken = 0
            for client in clients:
                # fetch the first page so we get the total count from the backend
                response = client.list(
                    "zaak", request_kwargs={"headers": {"Accept-Crs": "EPSG:4326"}}
                )
                client_num_zaken = response["count"]
                total_expected_zaken += client_num_zaken
                self.stdout.write(
                    f"Number of ZAAKen in {client.base_url}:\n  {client_num_zaken}."
                )

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
                        "Fetching ZAAKen for client, query params: %r.",
                        query_params,
                    )
                    zaken, query_params = get_zaken_all_paginated(
                        client, query_params=query_params
                    )
                    perf_logger.info("Fetched %d ZAAKen.", len(zaken))
                    get_more = query_params.get("page", None)

                    perf_logger.info("Entering ES documents generator.")
                    perf_logger.info("Memory usage: %s.", get_memory_usage())
                    yield from self.documenten_generator(zaken)
                    perf_logger.info("Exited ES documents generator.")

        else:
            for zaak in zaken:
                yield from self.documenten_generator([zaak])

        self.stdout.end_progress()

    def documenten_generator(
        self, zaken: List[Zaak]
    ) -> Iterator[ZaakInformatieObjectDocument]:
        perf_logger.info("  In ES documents generator.")
        perf_logger.info("    Create ZAAKINFORMATIEOBJECT documents...")
        zaakinformatieobjecten_documenten = self.create_zaakinformatieobject_documenten(
            zaken
        )
        perf_logger.info("    Create ZAAKINFORMATIEOBJECT documents finished.")
        for zio in zaakinformatieobjecten_documenten:
            ziod = zio.to_dict(True)
            yield ziod

    def create_zaakinformatieobject_documenten(
        self, zaken: List[Zaak]
    ) -> List[ZaakInformatieObjectDocument]:
        # Prefetch zaakinformatieobjecten
        with parallel(max_workers=self.max_workers) as executor:
            list_of_zios = list(executor.map(get_zaak_informatieobjecten, zaken))

        zaakinformatieobject_documenten = [
            create_zaakinformatieobject_document(zio)
            for zios in list_of_zios
            for zio in zios
            if zios
        ]
        num_case_zios = len(zaakinformatieobject_documenten)
        self.stdout.write_without_progress(
            f"{num_case_zios} ZAAKINFORMATIEOBJECTen are found for {len(zaken)} ZAAKen."
        )
        return zaakinformatieobject_documenten
