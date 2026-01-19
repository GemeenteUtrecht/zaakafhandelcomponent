from typing import Any, Dict

from zac.core.cache import invalidate_informatieobjecttypen_cache

Notification = Dict[str, Any]


class InformatieObjecttypenHandler:
    def handle(self, data: Notification) -> None:
        if data.get("resource") == "informatieobjecttype" and data.get("actie") in {
            "create",
            "update",
            "partial_update",
        }:
            catalogus = data.get("kenmerken", {}).get("catalogus")
            if catalogus:
                invalidate_informatieobjecttypen_cache(catalogus=catalogus)
            invalidate_informatieobjecttypen_cache()
