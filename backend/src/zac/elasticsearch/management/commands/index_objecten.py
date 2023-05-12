import logging
from typing import Dict, Iterator, List

from django.conf import settings
from django.core.management import BaseCommand
from django.core.management.base import CommandParser

from elasticsearch.helpers import bulk
from elasticsearch_dsl import Index
from elasticsearch_dsl.connections import connections
from elasticsearch_dsl.query import Bool, Nested, Terms

from zac.core.services import (
    fetch_objects_all_paginated,
    fetch_objecttypes,
    get_objects_client,
)

from ...api import (
    create_object_document,
    create_objecttype_document,
    create_related_zaak_document,
)
from ...documents import (
    ObjectDocument,
    ObjectTypeDocument,
    RelatedZaakDocument,
    ZaakDocument,
)
from ...utils import check_if_index_exists
from ..utils import ProgressOutputWrapper

perf_logger = logging.getLogger("performance")


class Command(BaseCommand):
    """
    Based on the OBJECTS V1 API - TODO migrate to V2 for pagination support.

    """

    help = "Create documents in ES by indexing all objecten from OBJECTS API. Requires zaken to be indexed already."
    index = settings.ES_INDEX_OBJECTEN

    def add_arguments(self, parser: CommandParser) -> None:
        super().add_arguments(parser)
        parser.add_argument(
            "--max-workers",
            type=int,
            help="Indicates the max number of parallel workers (for memory management). Defaults to 4.",
            default=4,
        )
        parser.add_argument(
            "--progress",
            "--show-progress",
            action="store_true",
            help=(
                "Show a progress bar. Showing a progress bar disables other "
                "fine-grained feedback."
            ),
        )

    def handle(self, **options):
        # redefine self.stdout as ProgressOutputWrapper cause logging is dependent whether
        # we have a progress bar
        show_progress = options["progress"]
        self.stdout = ProgressOutputWrapper(show_progress, out=self.stdout._out)

        self.max_workers = options["max_workers"]
        self.es_client = connections.get_connection()
        self.handle_indexing()

    def handle_indexing(self):
        # If we're indexing everything - clear the index.
        self.clear_index()
        ObjectDocument.init()
        self.bulk_upsert()
        index = Index(settings.ES_INDEX_OBJECTEN)
        index.refresh()
        count = index.search().count()
        self.stdout.write(f"{count} objects are received from OBJECTS API.")

    def bulk_upsert(self):
        bulk(
            self.es_client,
            self.batch_index(),
        )

    def zaken_index_exists(self) -> bool:
        check_if_index_exists(index=settings.ES_INDEX_ZAKEN)

    def batch_index(self) -> Iterator[ObjectDocument]:
        self.zaken_index_exists()
        self.stdout.write("Preloading all object types...")
        ots = {ot["url"]: ot for ot in fetch_objecttypes()}
        self.stdout.write(f"Fetched {len(ots)} object types.")
        self.stdout.write("Starting object retrieval from the configured OBJECTs API.")
        client = get_objects_client()

        query_params = {"pageSize": 100}
        get_more = True
        while get_more:
            objects, query_params = fetch_objects_all_paginated(
                client, query_params=query_params
            )
            perf_logger.info("Fetched %d objects", len(objects["results"]))
            get_more = query_params.get("page", None)
            for obj in objects["results"]:
                obj["type"] = ots[obj["type"]]

            yield from self.documenten_generator(objects["results"])

    def documenten_generator(self, objects: List[Dict]) -> Iterator[ObjectDocument]:
        object_documenten = self.create_objecten_documenten(objects)
        objecttype_documenten = self.create_objecttype_documenten(objects)
        zaken = (
            ZaakDocument.search()
            .filter(
                Nested(
                    path="zaakobjecten",
                    query=Bool(
                        filter=Terms(
                            zaakobjecten__object=[obj["url"] for obj in objects]
                        )
                    ),
                )
            )
            .source(
                [
                    "identificatie",
                    "url",
                    "omschrijving",
                    "bronorganisatie",
                    "zaakobjecten.object",
                    "zaaktype",
                    "vertrouwelijkheidaanduiding",
                ]
            )
            .execute()
        )
        related_zaken = self.create_related_zaken(zaken)
        for obj in objects:
            object_document = object_documenten[obj["url"]]
            object_document.type = objecttype_documenten[obj["url"]]
            object_document.related_zaken = related_zaken.get(obj["url"], [])
            od = object_document.to_dict(True)
            yield od

    def clear_index(self):
        index = Index(self.index)
        index.delete(ignore=404)

    def create_related_zaken(
        self, zaken: List[ZaakDocument]
    ) -> Dict[str, RelatedZaakDocument]:
        obj_to_zaken = {}
        for zaak in zaken:
            related_zaak = create_related_zaak_document(zaak)
            for obj in zaak.zaakobjecten:
                try:
                    obj_to_zaken[obj.object].append(related_zaak)
                except KeyError:
                    obj_to_zaken[obj.object] = [related_zaak]

        return obj_to_zaken

    def create_objecten_documenten(
        self, objects: List[Dict]
    ) -> Dict[str, ObjectDocument]:
        return {obj["url"]: create_object_document(obj) for obj in objects}

    def create_objecttype_documenten(
        self, objects: List[Dict]
    ) -> Dict[str, ObjectTypeDocument]:
        return {obj["url"]: create_objecttype_document(obj["type"]) for obj in objects}
