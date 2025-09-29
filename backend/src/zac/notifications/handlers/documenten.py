from typing import Any, Dict

from zac.core.cache import (
    invalidate_document_other_cache,
    invalidate_document_url_cache,
)
from zac.core.services import get_document
from zac.elasticsearch.api import (
    delete_informatieobject_document,
    update_informatieobject_document,
    update_related_zaken_in_informatieobject_document,
)

Notification = Dict[str, Any]


class InformatieObjectenHandler:
    """Handlers for kanaal='documenten' (EIO)."""

    def handle(self, data: Notification) -> None:
        if data.get("resource") != "enkelvoudiginformatieobject":
            return

        actie = data.get("actie")
        eio_url = data["hoofd_object"]

        if actie in {"create", "update", "partial_update"}:
            invalidate_document_url_cache(eio_url)
            document = get_document(eio_url)
            invalidate_document_other_cache(document)
            update_informatieobject_document(document)

            if actie == "create":
                update_related_zaken_in_informatieobject_document(document.url)

        elif actie == "destroy":
            invalidate_document_url_cache(eio_url)
            delete_informatieobject_document(eio_url)
