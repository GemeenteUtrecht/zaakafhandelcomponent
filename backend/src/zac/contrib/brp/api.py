import logging
import uuid
from typing import Optional

import requests
from zds_client import ClientError
from zds_client.schema import get_operation_url
from zgw_consumers.api_models.base import factory
from zgw_consumers.constants import AuthTypes

from zac.utils.decorators import cache as cache_result
from zac.zgw_client import ZGWClient

from .data import (
    ExtraInformatieIngeschrevenNatuurlijkPersoon,
    IngeschrevenNatuurlijkPersoon,
)
from .models import BRPConfig

logger = logging.getLogger(__name__)

from zac.core.utils import A_DAY


class HalClient(ZGWClient):
    def pre_request(self, method, url, **kwargs):
        """
        Add authorization header to requests for APIs without jwt.
        """

        result = super().pre_request(method, url, **kwargs)

        headers = kwargs.get("headers", {})
        headers["Accept"] = "application/hal+json"
        headers["Content-Type"] = "application/hal+json"
        return result


def get_client() -> HalClient:
    config = BRPConfig.get_solo()
    service = config.service

    assert service, "A service must be configured first"

    # Use zgw-consumers 1.x build_client pattern
    from zgw_consumers.client import build_client

    client = build_client(service, client_factory=HalClient)

    return client


def call_halclient_retrieve(
    client: HalClient,
    resource: str,
    url: Optional[str] = None,
    request_kwargs: Optional[dict] = None,
    **path_kwargs,
) -> dict:
    """Function that calls HalClient.retrieve (GET) and handles client exceptions
    when the response status equals 404 or 500.

    Args:
        client: HalClient
        resource: The resource that will be called
        url: Kwarg that specifies the url where the resource will be pulled from.
        request_kwargs: Dict that can include headers or request parameters.
        path_kwargs: Dict that includes the path kwargs according to the schema.

    Returns:
        JSON response from requests.request with information
        on the specified resource.
    """

    try:
        return client.retrieve(
            resource,
            url=url,
            request_kwargs=request_kwargs,
            **path_kwargs,
        )

    except ClientError as exc:
        if exc.args[0]["status"] == 404:
            logger.warning("Invalid BRP reference submitted: %s", url, exc_info=True)
            return None
        raise
    except requests.RequestException as exc:
        if exc.response.status_code == 500:
            logger.warning("BRP API is broken", exc_info=True)
            return None
        raise


@cache_result("natuurlijkpersoon:{url}", timeout=A_DAY)
def fetch_natuurlijkpersoon(url: str) -> IngeschrevenNatuurlijkPersoon:
    client = get_client()
    result = call_halclient_retrieve(client, "ingeschrevenNatuurlijkPersoon", url=url)
    return factory(IngeschrevenNatuurlijkPersoon, result)


def fetch_extrainfo_np(
    request_kwargs: Optional[dict] = None,
    **path_kwargs,
) -> ExtraInformatieIngeschrevenNatuurlijkPersoon:
    """Function that calls:
         get_client(),
         zds_client.schema.get_operation_url(),
         call_halclient_retrieve().

    Args:
        request_kwargs: Dict that can include headers or request parameters.
        path_kwargs: Dict that includes the path kwargs according to the schema.

    Returns:
        ExtraInformatieIngeschrevenNatuurlijkPersoon class filled in with
        result from call_halclient_retrieve function.
    """
    client = get_client()
    resource = "ingeschrevenNatuurlijkPersoon"
    url = get_operation_url(
        client.schema,
        resource,
        base_url=client.base_url,
        **path_kwargs,
    )

    result = call_halclient_retrieve(
        client,
        resource,
        url=url,
        request_kwargs=request_kwargs,
        **path_kwargs,
    )
    return factory(ExtraInformatieIngeschrevenNatuurlijkPersoon, result)
