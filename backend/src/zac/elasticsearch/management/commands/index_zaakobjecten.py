import logging
from typing import Iterator, List

from django.conf import settings
from django.core.management import BaseCommand

import click
from zgw_consumers.concurrent import parallel
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from zac.core.services import get_zaakobjecten, get_zaken_all_paginated
from zgw.models import Zaak

from ...api import create_zaakobject_document
from ...documents import ZaakDocument, ZaakObjectDocument
from ..utils import get_memory_usage

perf_logger = logging.getLogger("performance")

from .base_index import IndexCommand


class Command(IndexCommand, BaseCommand):
    help = "Create documents in ES by indexing all ZAAKOBJECTen from ZAKEN API"
    _index = settings.ES_INDEX_ZO
    _type = "zaakobject"
    _document = ZaakObjectDocument
    _verbose_name_plural = "ZAAKOBJECTen"
    relies_on = {
        settings.ES_INDEX_ZAKEN: ZaakDocument,
    }

    def batch_index(self) -> Iterator[ZaakObjectDocument]:
        super().batch_index()
        self.stdout.write(
            f"Starting {self._verbose_name_plural} retrieval from the configured APIs."
        )
        zrcs = Service.objects.filter(api_type=APITypes.zrc)
        clients = [zrc.build_client() for zrc in zrcs]
        # report back which clients will be iterated over and how many zaken each has
        total_expected_zaken = 0
        for client in clients:
            # fetch the first page so we get the total count from the backend
            response = client.list("zaak")
            client_num_zaken = response["count"]
            total_expected_zaken += client_num_zaken
            self.stdout.write(
                f"Number of ZAAKen in {client.base_url}:\n  {client_num_zaken}"
            )

        if self.reindex_last:
            total_expected_zaken = min(total_expected_zaken, self.reindex_last)

        if not self.reindex_last:
            self.stdout.write("Now the real work starts, hold on!")
            self.stdout.start_progress()
            with click.progressbar(
                length=total_expected_zaken,
                label="Indexing ",
                file=self.stdout.progress_file(),
            ) as bar:
                for client in clients:
                    perf_logger.info("Starting indexing for client %s", client)
                    perf_logger.info("Memory usage: %s", get_memory_usage())
                    get_more = True
                    # Set ordering explicitely
                    # FIXME: this implicitly assumes the generated or created identification
                    # contains some sort of time-stamp and/or increasing number for more recent
                    # cases. This is an assumption that can easily be thwarted, as clients have
                    # the ability to pick a unique identification themselves (such as UUIDs).
                    query_params = {"ordering": "-identificatie"}
                    while get_more:
                        # if this is running for 1h+, Open Zaak expires the token
                        client.refresh_auth()
                        perf_logger.info(
                            "Fetching cases for client, query params: %r", query_params
                        )
                        perf_logger.info("Memory usage: %s", get_memory_usage())
                        zaken, query_params = get_zaken_all_paginated(
                            client, query_params=query_params
                        )
                        perf_logger.info("Fetched %d cases", len(zaken))
                        perf_logger.info("Memory usage: %s", get_memory_usage())
                        # Make sure we're not retrieving more information than necessary on the zaken
                        if (
                            self.reindex_last
                            and self.reindex_last - self.reindexed <= len(zaken)
                        ):
                            zaken = zaken[: self.reindex_last - self.reindexed]

                        get_more = query_params.get("page", None)

                        perf_logger.info("Entering ES documents generator")
                        perf_logger.info("Memory usage: %s", get_memory_usage())
                        yield from self.documenten_generator(zaken)
                        perf_logger.info("Exited ES documents generator")
                        perf_logger.info("Memory usage: %s", get_memory_usage())
                        bar.update(len(zaken))

                    if self.check_if_done_batching():
                        self.stdout.end_progress()
                        return
        else:
            zaken = self.handle_reindex()
            for zaak in zaken:
                yield from self.documenten_generator([zaak])

        self.stdout.end_progress()

    def documenten_generator(self, zaken: List[Zaak]) -> Iterator[ZaakObjectDocument]:
        perf_logger.info("  In ES documents generator")
        perf_logger.info("    Create ZAAKOBJECT documents...")
        zaakobjecten_documenten = self.create_zaakobject_documenten(zaken)
        perf_logger.info("    Create ZAAKOBJECT documents finished")
        for zo in zaakobjecten_documenten:
            zd = zo.to_dict(True)
            yield zd
            if self.reindex_last:
                self.reindexed += 1
                if self.check_if_done_batching():
                    return

    def create_zaakobject_documenten(
        self, zaken: List[Zaak]
    ) -> List[ZaakObjectDocument]:
        # Prefetch zaakobjecten
        with parallel(max_workers=self.max_workers) as executor:
            list_of_zon = list(executor.map(get_zaakobjecten, zaken))

        zaakobjecten_documenten = [
            create_zaakobject_document(zo) for zon in list_of_zon for zo in zon if zon
        ]
        num_case_zos = len(zaakobjecten_documenten)
        self.stdout.write_without_progress(
            f"{num_case_zos} ZAAKOBJECTen are found for {len(zaken)} ZAAKen."
        )
        return zaakobjecten_documenten
