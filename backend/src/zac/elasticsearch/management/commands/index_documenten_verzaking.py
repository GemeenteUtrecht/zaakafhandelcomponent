import logging
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

from zac.core.services import (
    fetch_latest_audit_trail_data_document,
    resolve_documenten_informatieobjecttypen,
)
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

    def batch_index(self) -> Iterator[InformatieObjectDocument]:
        self.zaken_index_exists()
        self.zaakinformatieobjecten_index_exists()

        self.stdout.write(
            f"Starting {self.verbose_name_plural} retrieval from the configured APIs."
        )

        drc = Service.objects.get(api_type=APITypes.drc)
        client = drc.build_client()

        # report back which clients will be iterated over and how many zaken each has
        total_expected = ZaakInformatieObjectDocument.search().extra(size=0).count()
        max_j, remainder = divmod(total_expected, self.chunk_size)
        remainder = min([self.chunk_size, total_expected % self.chunk_size])
        self.stdout.write(f"Total number of ZIOs: {total_expected}.")
        self.stdout.write("Now the real work starts, hold on!")
        self.stdout.start_progress()
        perf_logger.info("Memory usage 1: %s.", get_memory_usage())

        # set loop parameters
        i = 0  # total zios collected
        j = 0  # total loops

        get_more = True if i < total_expected else False
        while get_more:
            perf_logger.info("Memory usage 2: %s.", get_memory_usage())
            # if this is running for 1h+ DRC expires the token
            client.refresh_auth()

            start = j * self.chunk_size
            end = (
                (j + 1) * self.chunk_size
                if j != max_j
                else j * self.chunk_size + remainder
            )
            if start == end:
                get_more = False
                break

            zios = ZaakInformatieObjectDocument.search()[start:end].execute()
            eios = list({zio.informatieobject for zio in zios})
            self.stdout.write(f"Retrieved EIOs: {len(eios)}.")

            # remove those who are already indexed
            already_indexed = search_informatieobjects(
                size=len(eios), urls=eios, fields=["url"]
            )
            already_indexed = [eio.url for eio in already_indexed]
            eios = [eio for eio in eios if eio not in already_indexed]
            self.stdout.write(f"Indexable EIOs: {len(eios)}.")
            if eios:
                self.headers = client.auth.credentials()
                with parallel(max_workers=self.max_workers) as executor:
                    responses = list(executor.map(self.make_request, eios))
                documenten = [
                    factory(Document, resp.json())
                    for resp in responses
                    if resp.status_code == 200
                ]
                perf_logger.info("Memory usage 3: %s.", get_memory_usage())
                yield from self.documenten_generator(documenten)

            self.stdout.write(f"Number of ZIOs left: {total_expected-end}.")
            # update loop parameters
            i += len(zios)
            j += 1
            if i >= total_expected:
                get_more = False
                self.stdout.end_progress()
                break

        self.stdout.end_progress()

    def resolve_documenten_informatieobjecttypen(
        self, documenten: List[Document]
    ) -> List[Document]:
        return resolve_documenten_informatieobjecttypen(documenten)

    def resolve_audit_trail(self, documenten: List[Document]) -> List[Document]:
        # bulk resolve fetch_audittrail
        with parallel() as executor:
            audittrails = list(
                executor.map(
                    fetch_latest_audit_trail_data_document,
                    [doc.url for doc in documenten],
                )
            )
            last_edited_dates = {
                at.resource_url: at.last_edited_date for at in audittrails if at
            }

        # bulk pre-resolve audittrails
        for doc in documenten:
            doc.last_edited_date = last_edited_dates.get(doc.url, None)
        return documenten

    def resolve_related_zaken(
        self, documenten: List[Document]
    ) -> Dict[str, List[RelatedZaakDocument]]:
        zios = (
            ZaakInformatieObjectDocument.search()
            .filter(Terms(informatieobject=[doc.url for doc in documenten]))
            .source(
                [
                    "zaak",
                    "informatieobject",
                ]
            )
            .execute()
        )
        zaken = (
            ZaakDocument.search()
            .filter(Terms(url=[zio.zaak for zio in zios]))
            .execute()
        )
        return self.create_related_zaken(zios, zaken)

    def documenten_generator(
        self, documenten: List[Document]
    ) -> Iterator[InformatieObjectDocument]:
        # Resolve informatieobjecttypen
        documenten = self.resolve_documenten_informatieobjecttypen(documenten)

        # Resolve audit trail
        documenten = self.resolve_audit_trail(documenten)

        # Create related_zaken
        related_zaken = self.resolve_related_zaken(documenten)

        # Create EIO documenten
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

    def create_related_zaken(
        self, zios: List[ZaakInformatieObjectDocument], zaken: List[ZaakDocument]
    ) -> Dict[str, RelatedZaakDocument]:
        related_zaken = {zaak.url: create_related_zaak_document(zaak) for zaak in zaken}
        found = 0
        eio_to_zaken = {}
        for zio in zios:
            related_zaak = related_zaken.get(zio.zaak, None)
            if related_zaak:
                try:
                    eio_to_zaken[zio.informatieobject].append(related_zaak)
                except KeyError:
                    eio_to_zaken[zio.informatieobject] = [related_zaak]

                found += 1

        self.stdout.write_without_progress(
            "{found} ENKELVOUDIGINFORMATIEOBJECTen are found for {zaken} related ZAAKen.".format(
                found=found, zaken=len(zaken)
            )
        )
        return eio_to_zaken

    def create_eio_documenten(
        self, documenten: List[Document]
    ) -> Dict[str, InformatieObjectDocument]:
        self.stdout.write_without_progress(
            "{no} ENKELVOUDIGINFORMATIEOBJECTen are found.".format(no=len(documenten))
        )
        return {doc.url: create_informatieobject_document(doc) for doc in documenten}
