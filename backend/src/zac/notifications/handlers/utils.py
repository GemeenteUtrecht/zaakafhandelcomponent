import logging
from typing import Any

from elasticsearch.exceptions import NotFoundError
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.zaken import Status

from zac.core.services import client_from_url, fetch_zaaktype, get_statustype
from zac.elasticsearch.api import (
    update_related_zaak_in_informatieobject_documents,
    update_related_zaak_in_object_documents,
)
from zgw.models.zrc import Zaak

logger = logging.getLogger(__name__)


def retrieve_zaak(zaak_url: str) -> Zaak:
    """Retrieve Zaak and resolve zaaktype + status/statustype."""
    zrc_client = client_from_url(zaak_url)
    zaak_dict: dict[str, Any] = zrc_client.retrieve(
        "zaak",
        url=zaak_url,
        request_kwargs={"headers": {"Accept-Crs": "EPSG:4326"}},
    )
    zaak = factory(Zaak, zaak_dict)

    if isinstance(zaak.zaaktype, str):
        zaak.zaaktype = fetch_zaaktype(zaak.zaaktype)

    if zaak.status and isinstance(zaak.status, str):
        status_dict = zrc_client.retrieve("status", url=zaak.status)
        status = factory(Status, status_dict)
        status.statustype = get_statustype(status.statustype)
        zaak.status = status

    return zaak


def soft_update_related_zaak_in_objects(zaak: Zaak) -> None:
    try:
        update_related_zaak_in_object_documents(zaak)
    except NotFoundError:
        logger.warning("Could not find objecten index.", exc_info=False)


def soft_update_related_zaak_in_docs(zaak: Zaak) -> None:
    try:
        update_related_zaak_in_informatieobject_documents(zaak)
    except NotFoundError:
        logger.warning("Could not find informatieobjecten index.", exc_info=False)
