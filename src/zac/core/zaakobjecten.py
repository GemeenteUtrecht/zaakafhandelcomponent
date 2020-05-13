from dataclasses import dataclass
from typing import Any, Dict, Iterator

import requests
from zgw_consumers.api_models.zaken import ZaakObject

from zac.contrib.kadaster.bag import fetch_pand, fetch_verblijfsobject


@dataclass
class ZaakObjectGroup:
    """
    Configure per ObjectType how it should be retrieved and how it should be rendered.
    """

    label: str
    retriever: callable = requests.get
    template: str = "core/includes/zaakobjecten/default.html"
    items: list = None

    def retrieve_items(self, items: Iterator[ZaakObject]) -> None:
        self.items = [self.retriever(item.object) for item in items]


def fetch_overige(url: str) -> Dict[str, Any]:
    return {"url": url}


GROUPS = {
    "pand": ZaakObjectGroup(
        label="Panden",
        retriever=fetch_pand,
        template="core/includes/zaakobjecten/pand.html",
    ),
    "verblijfsobject": ZaakObjectGroup(
        label="Verblijfsobjecten",
        retriever=fetch_verblijfsobject,
        template="core/includes/zaakobjecten/verblijfsobject.html",
    ),
}
