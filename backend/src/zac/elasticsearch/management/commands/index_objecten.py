import logging
from typing import Dict, Iterator, List

from django.conf import settings
from django.core.management import BaseCommand

from elasticsearch_dsl.query import Term, Terms

from zac.core.cache import invalidate_fetch_object_cache
from zac.core.models import MetaObjectTypesConfig
from zac.core.services import (
    fetch_objects,
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
    ZaakObjectDocument,
)
from .base_index import IndexCommand

perf_logger = logging.getLogger("performance")


class Command(IndexCommand, BaseCommand):
    help = "Create documents in ES by indexing all OBJECTen from OBJECTS API. Requires ZAAKen and ZAAKOBJECTen to be indexed already."
    _index = settings.ES_INDEX_OBJECTEN
    _type = "object"
    _document = ObjectDocument
    _verbose_name_plural = "OBJECTen"
    _index = settings.ES_INDEX_OBJECTEN
    relies_on = {
        settings.ES_INDEX_ZAKEN: ZaakDocument,
        settings.ES_INDEX_ZO: ZaakObjectDocument,
    }

    @property
    def meta_config_urls(self) -> List[str]:
        if not hasattr(self, "_meta_config_urls"):
            self._meta_config_urls = list(
                MetaObjectTypesConfig.get_solo().meta_objecttype_urls.values()
            )
        return self._meta_config_urls

    def batch_index(self) -> Iterator[ObjectDocument]:
        super().batch_index()
        self.stdout.write("Preloading all OBJECTTYPEn...")
        ots = {ot["url"]: ot for ot in fetch_objecttypes()}
        self.stdout.write(f"Fetched {len(ots)} OBJECTTYPEn.")
        self.stdout.write("Starting OBJECT retrieval from the configured OBJECTs API.")
        client = get_objects_client()

        zaken = self.get_zaken()

        if not zaken:
            query_params = {"pageSize": 100}
            get_more = True
            while get_more:
                objects, query_params = fetch_objects_all_paginated(
                    client, query_params=query_params
                )
                objects["results"] = [
                    obj
                    for obj in objects["results"]
                    if obj["type"] not in self.meta_config_urls
                ]
                perf_logger.info("Fetched %d OBJECTen.", len(objects["results"]))
                get_more = query_params.get("page", None)
                for obj in objects["results"]:
                    obj["type"] = ots[obj["type"]]

                yield from self.documenten_generator(objects["results"])
        else:
            for zaak in zaken:
                # First check to see if there are any zaakobjecten here before we iterate through a scan.
                if (
                    ZaakObjectDocument.search()
                    .extra(size=0)
                    .filter(Term(zaak=zaak.url))
                    .count()
                    == 0
                ):
                    # continue to next loop
                    continue

                zon_scan = (
                    ZaakObjectDocument.search()
                    .filter(Term(zaak=zaak.url))
                    .params(scroll="15h")
                    .scan()
                )
                for zon in self.get_chunks(zon_scan):
                    # Refresh client authentication in case this entire index takes longer than validatity of authentication token.
                    client.refresh_auth()

                    # Create list from chunk of generator.
                    zon = list(zon)

                    # Get unique OBJECTs urls.
                    objects = list({zo.object for zo in zon})

                    # Log total OBJECTs found.
                    self.stdout.write(f"OBJECTs from ZOs: {len(objects)}.")

                    # Invalidate cache
                    for obj in objects:
                        invalidate_fetch_object_cache(obj)

                    # Log number of OBJECTs to fetch.
                    self.stdout.write(f"Fetching OBJECTs: {len(objects)}.")

                    if zon:
                        # Fetch objects from OBJECTs API.
                        objects = fetch_objects(objects, max_workers=self.max_workers)
                        objects = [
                            obj
                            for obj in objects
                            if obj["type"]["url"] not in self.meta_config_urls
                        ]

                        if objects:
                            # Log how many were retrieved.
                            self.stdout.write(
                                f"Retrieved OBJECTs from OBJECTs API: {len(objects)}."
                            )
                            yield from self.documenten_generator(objects)

    def documenten_generator(self, objects: List[Dict]) -> Iterator[ObjectDocument]:
        object_documenten = self.create_objecten_documenten(objects)
        objecttype_documenten = self.create_objecttype_documenten(objects)

        related_zaken = self.resolve_related_zaken(object_documenten)
        for obj in objects:
            object_document = object_documenten[obj["url"]]
            object_document.type = objecttype_documenten[obj["url"]]
            object_document.related_zaken = related_zaken.get(obj["url"], [])
            od = object_document.to_dict(True)
            yield od

    def create_related_zaken(
        self,
        zon: List[ZaakObjectDocument],
        zaken: List[ZaakDocument],
        obj_to_zaken: Dict[str, List[RelatedZaakDocument]],
    ) -> Dict[str, RelatedZaakDocument]:
        related_zaken = {zaak.url: create_related_zaak_document(zaak) for zaak in zaken}
        for zo in zon:
            related_zaak = related_zaken.get(zo.zaak, None)
            if related_zaak:
                try:
                    obj_to_zaken[zo.object].append(related_zaak)
                except KeyError:
                    obj_to_zaken[zo.object] = [related_zaak]
        return obj_to_zaken

    def resolve_related_zaken(
        self, object_documenten: Dict[str, ObjectDocument]
    ) -> Dict[str, RelatedZaakDocument]:
        zo_scan_obj = (
            ZaakObjectDocument.search()
            .filter(Terms(object=[url for url in object_documenten.keys()]))
            .source(
                [
                    "zaak",
                    "object",
                ]
            )
            .scan()
        )

        obj_to_zaken = dict()
        for zon in self.get_chunks(zo_scan_obj):
            zon = list(zon)
            zaak_urls = list({zo.zaak for zo in zon})
            zaken = ZaakDocument.search().filter(Terms(url=zaak_urls)).scan()
            obj_to_zaken = self.create_related_zaken(zon, zaken, obj_to_zaken)
        return obj_to_zaken

    def create_objecten_documenten(
        self, objects: List[Dict]
    ) -> Dict[str, ObjectDocument]:
        self.stdout.write_without_progress(
            "{no} OBJECTen are found.".format(no=len(objects))
        )
        return {obj["url"]: create_object_document(obj) for obj in objects}

    def create_objecttype_documenten(
        self, objects: List[Dict]
    ) -> Dict[str, ObjectTypeDocument]:
        return {obj["url"]: create_objecttype_document(obj["type"]) for obj in objects}
