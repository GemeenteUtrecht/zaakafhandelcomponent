import logging
from typing import Dict, Iterator, List

from django.conf import settings
from django.core.management import BaseCommand

import click
from elasticsearch_dsl.query import Bool, Nested, Terms
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.concurrent import parallel
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from zac.core.services import (
    fetch_latest_audit_trail_data_document,
    get_documenten_all_paginated,
    resolve_documenten_informatieobjecttypen,
)

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
    help = "Create documents in ES by indexing all ENKELVOUDIGINFORMATIEOBJECTen from DRC APIs. Requires zaken and zaakinformatieobjecten to already be indexed."
    _index = settings.ES_INDEX_DOCUMENTEN
    _type = "enkelvoudiginformatieobject"
    _document = InformatieObjectDocument
    _verbose_name_plural = "ENKELVOUDIGINFORMATIEOBJECTen"

    def zaken_index_exists(self) -> bool:
        return check_if_index_exists(index=settings.ES_INDEX_ZAKEN)

    def batch_index(self) -> Iterator[InformatieObjectDocument]:
        self.zaken_index_exists()
        self.stdout.write(
            f"Starting {self.verbose_name_plural} retrieval from the configured APIs."
        )

        drcs = Service.objects.filter(api_type=APITypes.drc)
        clients = [drc.build_client() for drc in drcs]

        # report back which clients will be iterated over and how many zaken each has
        total_expected = 0
        for client in clients:
            # fetch the first page so we get the total count from the backend
            response = client.list(self.type)
            client_total_num = response["count"]
            total_expected += client_total_num
            self.stdout.write(
                f"Number of {self.verbose_name_plural} in {client.base_url}:\n  {client_total_num}."
            )

        if self.reindex_last:
            total_expected = min(total_expected, self.reindex_last)

        self.stdout.write("Now the real work starts, hold on!")
        self.stdout.start_progress()

        with click.progressbar(
            length=total_expected,
            label="Indexing ",
            file=self.stdout.progress_file(),
        ) as bar:
            for client in clients:
                perf_logger.info("Starting indexing for client %s.", client)
                perf_logger.info("Memory usage: %s.", get_memory_usage())
                get_more = True
                query_params = {}
                while get_more:
                    # if this is running for 1h+ DRC expires the token
                    client.refresh_auth()
                    perf_logger.info(
                        "Fetching indexable objects for client, query params: %r.",
                        query_params,
                    )
                    documenten, query_params = get_documenten_all_paginated(
                        client, query_params=query_params
                    )

                    # resolve informatieobjecttypes
                    documenten = resolve_documenten_informatieobjecttypen(documenten)

                    # Make sure we're not retrieving more information than necessary
                    if self.reindex_last and self.reindex_last - self.reindexed <= len(
                        documenten
                    ):
                        documenten = documenten[: self.reindex_last - self.reindexed]

                    get_more = query_params.get("page", None)
                    yield from self.documenten_generator(documenten)
                    bar.update(len(documenten))

                if self.check_if_done_batching():
                    self.stdout.end_progress()
                    return

        self.stdout.end_progress()

    def documenten_generator(
        self, documenten: List[Document]
    ) -> Iterator[InformatieObjectDocument]:

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

        eio_documenten = self.create_eio_documenten(documenten)
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
        related_zaken = self.create_related_zaken(zios, zaken)
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
