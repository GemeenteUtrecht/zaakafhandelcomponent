import datetime
import logging
import time
from typing import Dict, Iterator, List

from django.conf import settings
from django.core.management import BaseCommand
from django.core.management.base import CommandParser

import requests
from elasticsearch_dsl.query import Terms
from requests.models import Response
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.concurrent import parallel
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from zac.core.services import resolve_documenten_informatieobjecttypen
from zac.elasticsearch.searches import search_informatieobjects

from ...api import create_informatieobject_document, create_related_zaak_document
from ...documents import (
    InformatieObjectDocument,
    RelatedZaakDocument,
    ZaakDocument,
    ZaakInformatieObjectDocument,
)
from ...utils import check_if_index_exists
from ..utils import get_memory_usage
from .base_index import IndexCommand

perf_logger = logging.getLogger("performance")


class Command(IndexCommand, BaseCommand):
    """
    #TODO: Warning: this is only a temporary indexing function. It's not as time efficient as index_documenten
    but until LIST endpoint of EIO is supported, this will have to be used.
    """

    help = "Create documents in ES by indexing all VERZAAKTE ENKELVOUDIGINFORMATIEOBJECTen from DRC APIs. Requires zaken and zaakinformatieobjecten to already be indexed."
    _index = settings.ES_INDEX_DOCUMENTEN
    _type = "enkelvoudiginformatieobject"
    _document = InformatieObjectDocument
    _verbose_name_plural = "ENKELVOUDIGINFORMATIEOBJECTen"

    def zaken_index_exists(self) -> bool:
        return check_if_index_exists(index=settings.ES_INDEX_ZAKEN)

    def zaakinformatieobjecten_index_exists(self) -> bool:
        return check_if_index_exists(index=settings.ES_INDEX_ZIO)

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--chunk-size",
            type=int,
            help="Indicates the chunk size for number of ZIOs in a single iteration. Defaults to 100.",
            default=100,
        )
        super().add_arguments(parser)

    def handle(self, **options):
        self.chunk_size = options["chunk_size"]
        super().handle(**options)

    def make_request(self, url) -> Response:
        return requests.get(url, headers=self.headers)

    def get_chunks(self, iterable):
        from itertools import chain, islice

        iterator = iter(iterable)
        for first in iterator:
            yield chain([first], islice(iterator, self.chunk_size - 1))

    def get_documenten(self, client, eios: List[str]) -> List[Document]:
        self.headers = client.auth.credentials()
        with parallel(max_workers=self.max_workers) as executor:
            responses = list(executor.map(self.make_request, eios))

        return [
            factory(Document, resp.json())
            for resp in responses
            if resp.status_code == 200
        ]

    def batch_index(self) -> Iterator[InformatieObjectDocument]:
        self.zaken_index_exists()
        self.zaakinformatieobjecten_index_exists()

        # Announce start.
        self.stdout.write(
            f"Starting {self.verbose_name_plural} retrieval from the configured DRC."
        )

        drc = Service.objects.get(api_type=APITypes.drc)
        client = drc.build_client()

        # report back which clients will be iterated over and how many zaken each has
        total_expected = ZaakInformatieObjectDocument.search().extra(size=0).count()

        # Log amount to be fetched.
        self.stdout.write(f"Total number of ZIOs: {total_expected}.")
        self.stdout.start_progress()

        # Log memory use before starting to iterate.
        perf_logger.info("Memory usage 1: %s.", get_memory_usage())

        # Use scan here because it can be a very large search
        zios_scan = ZaakInformatieObjectDocument.search().scan()

        # Get time and set done=0 at start to calculate finish time.
        time_at_start = time.time()
        done = 0

        for zios in self.get_chunks(zios_scan):
            # Log memory use in iterator.
            perf_logger.info("Memory usage 2: %s.", get_memory_usage())

            # Refresh client authentication in case this entire index takes longer than validatity of authentication token.
            client.refresh_auth()

            # Create list from chunk of generator.
            zios = list(zios)
            # Get unique EIO urls.
            eios = list({zio.informatieobject for zio in zios})

            # Log total EIOs found.
            self.stdout.write(f"EIOs from ZIOs: {len(eios)}.")

            # Remove EIOs that have already been indexed.
            already_indexed = search_informatieobjects(
                size=len(eios), urls=eios, fields=["url"]
            )
            already_indexed = [eio.url for eio in already_indexed]
            eios = [eio for eio in eios if eio not in already_indexed]

            # Log number of EIOs to fetch.
            self.stdout.write(f"Fetching EIOs: {len(eios)}.")

            if eios:
                # Fetch documenten from DRC.
                documenten = self.get_documenten(client, eios)

                # Log how many were retrieved.
                self.stdout.write(f"Retrieved EIOs from DRC: {len(documenten)}.")
                perf_logger.info("Memory usage 3: %s.", get_memory_usage())
                yield from self.documenten_generator(documenten)

            # Add to done.
            done += len(zios)

            # Log number left
            self.stdout.write(f"Number of ZIOs left: {total_expected-done}.")

            # Calculate time remaining.
            total_time = (total_expected / done) * (time.time() - time_at_start)
            days, left_over_seconds = divmod(total_time, 24 * 3600)
            hours, left_over = divmod(left_over_seconds, 3600)
            minutes, seconds = divmod(left_over, 60)

            # Print time remaining.
            self.stdout.write(
                f"Estimated time remaining {int(days)} days and {int(hours)} hours, {int(minutes)} minutes and {int(seconds)} seconds."
            )

            # Calculate finish datetime.
            datetime_now = datetime.datetime.now()
            datetime_finished = datetime_now + datetime.timedelta(
                days, left_over_seconds
            )

            # Print finish datetime.
            self.stdout.write(
                f"Estimated finish time: {datetime_finished.isoformat()}."
            )

        self.stdout.end_progress()

    def resolve_documenten_informatieobjecttypen(
        self, documenten: List[Document]
    ) -> List[Document]:
        return resolve_documenten_informatieobjecttypen(documenten)

    def resolve_audit_trail(self, documenten: List[Document]) -> List[Document]:
        for doc in documenten:
            doc.last_edited_date = None
        return documenten

    def resolve_related_zaken(
        self, documenten: List[Document]
    ) -> Dict[str, List[RelatedZaakDocument]]:
        zios_scan_eio = (
            ZaakInformatieObjectDocument.search()
            .filter(Terms(informatieobject=[doc.url for doc in documenten]))
            .source(
                [
                    "zaak",
                    "informatieobject",
                ]
            )
            .scan()
        )
        eio_to_zaken = dict()
        for zios in self.get_chunks(zios_scan_eio):
            zios = list(zios)
            zaak_urls = list({zio.zaak for zio in zios})
            zaken = ZaakDocument.search().filter(Terms(url=zaak_urls)).scan()
            eio_to_zaken = self.create_related_zaken(zios, zaken, eio_to_zaken)
        return eio_to_zaken

    def create_related_zaken(
        self,
        zios: List[ZaakInformatieObjectDocument],
        zaken: List[ZaakDocument],
        eio_to_zaken: Dict[str, List[RelatedZaakDocument]],
    ) -> Dict[str, RelatedZaakDocument]:
        related_zaken = {zaak.url: create_related_zaak_document(zaak) for zaak in zaken}
        for zio in zios:
            related_zaak = related_zaken.get(zio.zaak, None)
            if related_zaak:
                try:
                    eio_to_zaken[zio.informatieobject].append(related_zaak)
                except KeyError:
                    eio_to_zaken[zio.informatieobject] = [related_zaak]
        return eio_to_zaken

    def documenten_generator(
        self, documenten: List[Document]
    ) -> Iterator[InformatieObjectDocument]:
        # Resolve informatieobjecttypen.
        documenten = self.resolve_documenten_informatieobjecttypen(documenten)

        # Resolve audit trail - in this function set to None.
        documenten = self.resolve_audit_trail(documenten)

        # Create related_zaken.
        related_zaken = self.resolve_related_zaken(documenten)

        self.stdout.write(
            f"Found {sum([len(val) for key,val in related_zaken.items()])} related ZAAKen for {len(related_zaken)} EIOs."
        )

        # Create EIO documenten.
        eio_documenten = self.create_eio_documenten(documenten)

        # Join and yield
        for doc in documenten:
            eio_document = eio_documenten[doc.url]
            eio_document.related_zaken = related_zaken.get(doc.url, [])
            eiod = eio_document.to_dict(True, skip_empty=False)
            yield eiod
            if self.reindex_last:
                self.reindexed += 1
                if self.check_if_done_batching():
                    return

    def create_eio_documenten(
        self, documenten: List[Document]
    ) -> Dict[str, InformatieObjectDocument]:
        self.stdout.write_without_progress(
            "{no} ENKELVOUDIGINFORMATIEOBJECTen are found.".format(no=len(documenten))
        )
        return {doc.url: create_informatieobject_document(doc) for doc in documenten}
