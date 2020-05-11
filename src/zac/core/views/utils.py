from django.http import HttpRequest

from zgw_consumers.api_models.zaken import Zaak

from ..services import get_zaak


def get_zaak_from_query(request: HttpRequest, param: str = "zaak") -> Zaak:
    zaak_url = request.GET.get(param)
    if not zaak_url:
        raise ValueError(f"Expected '{param}' querystring parameter")

    zaak = get_zaak(zaak_url=zaak_url)
    return zaak
