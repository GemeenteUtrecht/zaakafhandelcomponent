from dataclasses import dataclass
from typing import Iterator

from django.conf import settings

from requests import Response
from zgw_consumers.api_models.zaken import ZaakObject

from zac.core.models import CoreConfig, MetaObjectTypesConfig
from zac.core.services import fetch_objects
from zac.utils.http import get_session


def _requests_get_with_timeout(url: str, **kwargs) -> Response:
    kwargs.setdefault("timeout", settings.REQUESTS_DEFAULT_TIMEOUT)
    return get_session().get(url, **kwargs)


def noop(url: str) -> str:
    return url


@dataclass
class ZaakObjectGroup:
    """
    Configure per ObjectType how it should be retrieved and how it should be rendered.
    """

    object_type: str
    label: str
    retriever: callable = _requests_get_with_timeout
    template: str = "core/includes/zaakobjecten/default.html"
    items: list = None

    def retrieve_items(
        self, items: Iterator[ZaakObject], exclude_meta: bool = True
    ) -> None:
        object_items = [
            (item.url, self.retriever(item.object)) if item.object else item
            for item in items
        ]

        # Resolve if some of the related objects are in the objects API
        config = CoreConfig.get_solo()
        object_api = config.primary_objects_api
        if not object_api:
            raise RuntimeError("No objects API has been configured yet.")

        object_url_in_object_api = {
            item
            for zaakobject_url, item in object_items
            if isinstance(item, str) and item.startswith(object_api.api_root)
        }
        objects_in_object_api = fetch_objects(list(object_url_in_object_api))
        object_url_mapping = {obj["url"]: obj for obj in objects_in_object_api}

        self.items = []

        # Do not show retrieved meta objects unless explicitly requested
        meta_objecttype_urls = list(
            MetaObjectTypesConfig.get_solo().meta_objecttype_urls.values()
        )
        for zaakobject_url, item in object_items:
            retrieved_item = object_url_mapping.get(item, item)
            if (
                retrieved_item.get("type", {}).get("url") in meta_objecttype_urls
                and exclude_meta
            ):
                continue

            # add zaakobject_url for all dict-like object items
            if isinstance(retrieved_item, dict):
                retrieved_item.update({"zaakobject_url": zaakobject_url})

            self.items.append(retrieved_item)


# TODO
GROUPS = {
    # "pand": ZaakObjectGroup(
    #     object_type="pand",
    #     label="Panden",
    #     retriever=fetch_pand,
    #     template="core/includes/zaakobjecten/pand.html",
    # ),
    # "verblijfsobject": ZaakObjectGroup(
    #     object_type="verblijfsobject",
    #     label="Verblijfsobjecten",
    #     retriever=fetch_verblijfsobject,
    #     template="core/includes/zaakobjecten/verblijfsobject.html",
    # ),
    # # Roxit Squit 20/20 POC
    # "adres": ZaakObjectGroup(
    #     object_type="adres",
    #     label="Adressen",
    #     template="core/includes/zaakobjecten/adres.html",
    # ),
    # "omgevingsdossier": ZaakObjectGroup(
    #     object_type="omgevingsdossier",
    #     label="Omgevingsdossiers",
    #     retriever=noop,
    #     template="core/includes/zaakobjecten/omgevingsdossier.html",
    # ),
}
