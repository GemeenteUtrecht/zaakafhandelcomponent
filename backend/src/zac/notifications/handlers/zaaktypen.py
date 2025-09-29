from typing import Any, Dict

from zac.core.cache import invalidate_zaaktypen_cache

Notification = Dict[str, Any]


class ZaaktypenHandler:
    def handle(self, data: Notification) -> None:
        if data.get("resource") == "zaaktype" and data.get("actie") in {
            "create",
            "update",
            "partial_update",
        }:
            catalogus = data.get("kenmerken", {}).get("catalogus")
            if catalogus:
                invalidate_zaaktypen_cache(catalogus=catalogus)
            invalidate_zaaktypen_cache()
