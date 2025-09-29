import logging
from typing import Any, Dict

from django_camunda.api import send_message
from requests.exceptions import HTTPError
from zgw_consumers.api_models.base import factory

from zac.contrib.objects.kownsl.cache import invalidate_review_requests_cache
from zac.contrib.objects.kownsl.data import ReviewRequest
from zac.contrib.objects.services import delete_zaakobjecten_of_object, fetch_object
from zac.core.cache import invalidate_fetch_object_cache
from zac.core.models import MetaObjectTypesConfig
from zac.elasticsearch.api import delete_object_document, update_object_document

logger = logging.getLogger(__name__)
Notification = Dict[str, Any]


class ObjectenHandler:
    """Handlers for kanaal='objecten'."""

    def _review_request_object_handler(self, obj_payload: dict) -> None:
        rr = factory(ReviewRequest, obj_payload["record"]["data"])
        invalidate_review_requests_cache(rr)
        if rr.locked:
            try:
                send_message("cancel-process", [rr.metadata.get("process_instance_id")])
            except HTTPError:
                logger.info(
                    "Failed to end process instance gracefully; it may not exist.",
                    exc_info=True,
                )

    def _meta_object_handlers(self) -> Dict[str, callable]:
        meta_config = MetaObjectTypesConfig.get_solo()
        return {
            meta_config.review_request_objecttype: self._review_request_object_handler
        }

    def handle(self, data: Notification) -> None:
        if data.get("resource") != "object":
            return

        hoofd_object = data["hoofd_object"]
        invalidate_fetch_object_cache(hoofd_object)

        actie = data.get("actie")
        if actie in {"create", "update", "partial_update"}:
            obj = fetch_object(hoofd_object)

            if (
                handler := self._meta_object_handlers().get(obj["type"]["url"])
            ) is not None:
                handler(obj)

            if (
                obj["type"]["url"]
                not in MetaObjectTypesConfig.get_solo().meta_objecttype_urls.values()
            ):
                update_object_document(obj)

        elif actie == "destroy":
            delete_object_document(hoofd_object)
            delete_zaakobjecten_of_object(hoofd_object)
