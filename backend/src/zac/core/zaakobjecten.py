from dataclasses import dataclass
from typing import Iterator

import requests
from zgw_consumers.api_models.zaken import ZaakObject

from zac.contrib.kadaster.bag import fetch_pand, fetch_verblijfsobject


def noop(url: str) -> str:
    return url


@dataclass
class ZaakObjectGroup:
    """
    Configure per ObjectType how it should be retrieved and how it should be rendered.
    """

    object_type: str
    label: str
    retriever: callable = requests.get
    template: str = "core/includes/zaakobjecten/default.html"
    items: list = None

    def retrieve_items(self, items: Iterator[ZaakObject]) -> None:
        self.items = [
            self.retriever(item.object) if item.object else item for item in items
        ]


GROUPS = {
    "pand": ZaakObjectGroup(
        object_type="pand",
        label="Panden",
        retriever=fetch_pand,
        template="core/includes/zaakobjecten/pand.html",
    ),
    "verblijfsobject": ZaakObjectGroup(
        object_type="verblijfsobject",
        label="Verblijfsobjecten",
        retriever=fetch_verblijfsobject,
        template="core/includes/zaakobjecten/verblijfsobject.html",
    ),
    # Roxit Squit 20/20 POC
    "adres": ZaakObjectGroup(
        object_type="adres",
        label="Adressen",
        template="core/includes/zaakobjecten/adres.html",
    ),
    "omgevingsdossier": ZaakObjectGroup(
        object_type="omgevingsdossier",
        label="Omgevingsdossiers",
        retriever=noop,
        template="core/includes/zaakobjecten/omgevingsdossier.html",
    ),
}
