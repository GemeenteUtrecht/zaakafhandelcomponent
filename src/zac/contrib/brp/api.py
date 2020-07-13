from zgw_consumers.api_models.base import factory
from zgw_consumers.models import Service

from zac.utils.decorators import cache as cache_result

from .data import IngeschrevenNatuurlijkPersoon

A_DAY = 60 * 60 * 24


@cache_result("natuurlijkpersoon:{url}", timeout=A_DAY)
def fetch_natuurlijkpersoon(url: str) -> IngeschrevenNatuurlijkPersoon:
    service = Service.get_service(url)
    client = service.build_client()
    result = client.retrieve("ingeschrevenNatuurlijkPersoon", url=url)
    return factory(IngeschrevenNatuurlijkPersoon, result)
