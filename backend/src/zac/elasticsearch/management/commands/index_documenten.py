import datetime
import logging
import time
from typing import Dict, Iterator, List, Optional, Tuple
from urllib.parse import urlsplit, urlunsplit

from django.conf import settings
from django.core.management import BaseCommand

import requests
from elasticsearch_dsl.query import Term, Terms
from requests.models import Response
from zgw_consumers.api_models.base import factory
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
from ..utils import get_memory_usage
from .base_index import IndexCommand

perf_logger = logging.getLogger("performance")
logger = logging.getLogger(__name__)


class Command(IndexCommand, BaseCommand):
    help = "Create documents in ES by indexing all VERZAAKTE ENKELVOUDIGINFORMATIEOBJECTen from DRC APIs. Requires zaken and zaakinformatieobjecten to already be indexed."
    _index = settings.ES_INDEX_DOCUMENTEN
    _type = "enkelvoudiginformatieobject"
    _document = InformatieObjectDocument
    _verbose_name_plural = "ENKELVOUDIGINFORMATIEOBJECTen"
    relies_on = {
        settings.ES_INDEX_ZAKEN: ZaakDocument,
        settings.ES_INDEX_ZIO: ZaakInformatieObjectDocument,
    }

    def get_request_args(
        self, clients, eio: str
    ) -> Optional[Tuple[Dict[str, str], str]]:
        split_url = urlsplit(eio)
        scheme_and_domain = urlunsplit(split_url[:2] + ("", "", ""))
        for base_url, client in clients.items():
            if base_url.startswith(scheme_and_domain):
                return (eio, client.auth.credentials())
        return None

    def make_request(self, url_with_header: Tuple[Dict[str, str], str]) -> Response:
        return requests.get(url_with_header[0], headers=url_with_header[1])

    def get_documenten(self, clients, eios: List[str]) -> List[Document]:
        requests_args = []
        for eio in eios:
            if request_args := self.get_request_args(clients, eio):
                requests_args.append(request_args)
            else:
                logger.warning("Did not find a client for %s." % eio)

        with parallel(max_workers=self.max_workers) as executor:
            responses = list(executor.map(self.make_request, requests_args))

        return [
            factory(Document, resp.json())
            for resp in responses
            if resp.status_code == 200
        ]

    def log_progress(self, total_expected, done, time_at_start):
        # Log number left
        self.stdout.write(f"Number of EIOs left: {total_expected-done}.")

        # Calculate time remaining.
        total_time = (
            ((total_expected - done) / done) * (time.time() - time_at_start)
            if done
            else 0
        )
        days, left_over_seconds = divmod(total_time, 24 * 3600)
        hours, left_over = divmod(left_over_seconds, 3600)
        minutes, seconds = divmod(left_over, 60)

        # Print time remaining.
        self.stdout.write(
            f"Estimated time remaining {int(days)} days and {int(hours)} hours, {int(minutes)} minutes and {int(seconds)} seconds."
        )

        # Calculate finish datetime.
        datetime_now = datetime.datetime.now()
        datetime_finished = datetime_now + datetime.timedelta(days, left_over_seconds)

        # Print finish datetime.
        self.stdout.write(f"Estimated finish time: {datetime_finished.isoformat()}.")

    def batch_index(self) -> Iterator[InformatieObjectDocument]:
        super().batch_index()
        # Announce start.
        self.stdout.write(
            f"Starting {self.verbose_name_plural} retrieval from the configured APIs."
        )
        drcs = Service.objects.filter(api_type=APITypes.drc)
        clients = {drc.api_root: drc.build_client() for drc in drcs}

        zaken = self.get_zaken()
        if not zaken:
            # Get all zaken from elasticsearch index and use reindex_last anyway.
            # See comment under next `if not zaken:`
            zaken = list(
                ZaakDocument.search().sort("-identificatie.keyword").execute().hits
            )
            self.reindex_last = len(zaken)

        if not zaken:
            # Currently not supported because alfresco endpoint crashes.
            # Use --reindex-last <total number of zaken:int> instead.

            # Get everything
            # Report back which clients will be iterated over and how many IOs each has.
            total_expected = 0
            for client in clients.values():
                # Fetch the first page so we get the total count to be fetched.
                response = client.list(self.type)
                client_total_num = response["count"]
                total_expected += client_total_num
                self.stdout.write(
                    f"Number of {self.verbose_name_plural} in {client.base_url}:\n  {client_total_num}."
                )
            self.stdout.start_progress()
            done = 0

            # Get time at start
            time_at_start = time.time()
            for client in clients.values():
                perf_logger.info("Starting indexing for client %s.", client)
                perf_logger.info("Memory usage: %s.", get_memory_usage())
                get_more = True
                query_params = {}
                while get_more:
                    # Refresh client authentication in case this entire index takes longer than validatity of authentication token.
                    client.refresh_auth()
                    perf_logger.info(
                        "Fetching indexable objects for client, query params: %r.",
                        query_params,
                    )
                    documenten, query_params = get_documenten_all_paginated(
                        client, query_params=query_params
                    )
                    get_more = query_params.get("page", None)
                    yield from self.documenten_generator(documenten)

                # Add to done.
                done += len(documenten)
                self.log_progress(total_expected, done, time_at_start)
        else:
            # First to basic checks and fetch <int:self.reindex_last> zaken.
            total = len(zaken)
            for i, zaak in enumerate(zaken):
                try:
                    # Check to see if there are any zaakinformatieobjecten here before we iterate through a scan.
                    if (
                        ZaakInformatieObjectDocument.search()
                        .extra(size=0)
                        .filter(Term(zaak=zaak.url))
                        .count()
                        == 0
                    ):
                        # continue to next zaak
                        continue

                    # Use scan here because it can be a very large search
                    zios_scan = (
                        ZaakInformatieObjectDocument.search()
                        .filter(Term(zaak=zaak.url))
                        .params(scroll="15h")
                        .scan()
                    )

                    for zios in self.get_chunks(zios_scan):
                        # Refresh client authentication in case this entire index takes longer than validatity of authentication token.
                        for client in clients.values():
                            client.refresh_auth()

                        # Create list from chunk of generator.
                        zios = list(zios)

                        # Get unique EIO urls.
                        eios = list({zio.informatieobject for zio in zios})

                        # Log total EIOs found.
                        self.stdout.write(f"Fetching EIOs from ZIOs: {len(eios)}.")

                        if eios:
                            # Fetch documenten from DRC.
                            documenten = self.get_documenten(clients, eios)

                            # Log how many were retrieved.
                            self.stdout.write(
                                f"Retrieved EIOs from DRC: {len(documenten)}."
                            )
                            perf_logger.info("Memory usage 3: %s.", get_memory_usage())
                            yield from self.documenten_generator(documenten)
                except Exception as exc:
                    logger.warning("Problem", exc_info=1)
                    self.stdout.write(f"Failed at zaak: {i+1}/{total}.")
                    self.stdout.write(f"Continue reindexing last: {total-i}.")

        self.stdout.end_progress()

    def resolve_documenten_informatieobjecttypen(
        self, documenten: List[Document]
    ) -> List[Document]:
        return resolve_documenten_informatieobjecttypen(documenten)

    def resolve_audit_trail(self, documenten: List[Document]) -> List[Document]:
        # Bulk fetch_audittrail.
        with parallel(max_workers=self.max_workers) as executor:
            audittrails = list(
                executor.map(
                    fetch_latest_audit_trail_data_document,
                    [doc.url for doc in documenten],
                )
            )
            last_edited_dates = {
                at.resource_url: at.last_edited_date for at in audittrails if at
            }

        # Bulk resolve audittrails.
        for doc in documenten:
            doc.last_edited_date = last_edited_dates.get(doc.url, None)

        return documenten

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

        # Create EIO documents in ES.
        eio_documenten = self.create_eio_documenten(documenten)

        # Join and yield
        for doc in documenten:
            eio_document = eio_documenten[doc.url]
            eio_document.related_zaken = related_zaken.get(doc.url, [])
            eiod = eio_document.to_dict(True, skip_empty=False)
            yield eiod

    def create_eio_documenten(
        self, documenten: List[Document]
    ) -> Dict[str, InformatieObjectDocument]:
        self.stdout.write_without_progress(
            "{no} ENKELVOUDIGINFORMATIEOBJECTen are found.".format(no=len(documenten))
        )
        return {doc.url: create_informatieobject_document(doc) for doc in documenten}
