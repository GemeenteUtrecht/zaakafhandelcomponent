from dataclasses import dataclass
from itertools import groupby
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


@dataclass
class ZaakObjectOverigeGroup(ZaakObjectGroup):
    retrievers: dict = None

    def retrieve_items(self, items: Iterator[ZaakObject]) -> None:
        overige_items = list(items)

        def group_key(zo):
            return zo.object_type_overige

        render_overige_groups = []
        overige_items = sorted(overige_items, key=group_key)
        grouped = groupby(overige_items, key=group_key)
        for overige_group, items in grouped:
            retriever = self.retrievers.get(overige_group, fetch_overige)
            rendered_items = [retriever(item.object) for item in items]
            render_overige_groups.append((overige_group, rendered_items))
        self.items = render_overige_groups


def fetch_overige(url: str) -> Dict[str, Any]:
    return {"url": url}


GROUPS = {
    "pand": ZaakObjectGroup(
        label="Panden",
        retriever=fetch_pand,
        template="core/includes/zaakobjecten/pand.html",
    ),
    "overige": ZaakObjectOverigeGroup(
        label="Overige",
        retrievers={"verblijfsobject": fetch_verblijfsobject},
        template="core/includes/zaakobjecten/overige.html",
    ),
}
