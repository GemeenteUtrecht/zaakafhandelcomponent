import uuid

from django.http import HttpRequest

from zgw_consumers.api_models.zaken import Zaak

from ..services import get_zaak


def get_zaak_from_query(request: HttpRequest, param: str = "zaak") -> Zaak:
    zaak_url = request.GET.get(param)
    if not zaak_url:
        raise ValueError(f"Expected '{param}' querystring parameter")

    zaak = get_zaak(zaak_url=zaak_url)
    return zaak


def get_uuid_from_path(path: str) -> str:
    if path.endswith("/"):
        path = path.rstrip("/")

    uuid_str = path.rsplit("/")[-1]

    # validate if it's a proper hex string
    uuid.UUID(uuid_str)

    return uuid_str
