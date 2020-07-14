import uuid

from zgw_consumers.api_models.base import factory
from zgw_consumers.client import ZGWClient
from zgw_consumers.constants import AuthTypes
from zgw_consumers.models import Service

from zac.utils.decorators import cache as cache_result

from .data import IngeschrevenNatuurlijkPersoon
from .models import BRPConfig

A_DAY = 60 * 60 * 24


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

    _uuid = uuid.uuid4()
    api_root = (
        service.api_root.replace(service.api_root, service.nlx, 1)
        if service.nlx
        else service.api_root
    )
    client = HalClient.from_url(f"{api_root}dummy/{_uuid}")
    client.schema_url = service.oas

    if service.auth_type == AuthTypes.api_key:
        client.auth_value = {service.header_key: service.header_value}

    return client


@cache_result("natuurlijkpersoon:{url}", timeout=A_DAY)
def fetch_natuurlijkpersoon(url: str) -> IngeschrevenNatuurlijkPersoon:
    client = get_client()
    result = client.retrieve("ingeschrevenNatuurlijkPersoon", url=url)
    return factory(IngeschrevenNatuurlijkPersoon, result)
