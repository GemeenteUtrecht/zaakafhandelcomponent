import itertools

from django.core.cache import cache

from zgw.models.zrc import Zaak
from zgw_consumers.client import Client


def invalidate_zaak_cache(zaak: Zaak):
    keys = [
        f"zaak:{zaak.bronorganisatie}:{zaak.identificatie}",
        f"get_zaak:{zaak.uuid}:{zaak.url}",
    ]

    for key in keys:
        cache.delete(key)


def invalidate_zaak_list_cache(client: Client, zaak: dict):
    zaaktypes = ("", zaak["zaaktype"])
    identificaties = ("", zaak["identificatie"])
    bronorganisaties = ("", zaak["bronorganisatie"])

    template = "zaken:{client.base_url}:{zaaktype}:{identificatie}:{bronorganisatie}"

    cache_keys = [
        template.format(
            client=client,
            **dict(zip(("zaaktype", "identificatie", "bronorganisatie"), prod)),
        )
        for prod in itertools.product(zaaktypes, identificaties, bronorganisaties)
    ]

    for key in cache_keys:
        cache.delete(key)
