from django.core.cache import cache

from zgw.models.zrc import Zaak


def invalidate_zaak_cache(zaak: Zaak):
    keys = [
        f"zaak:{zaak.bronorganisatie}:{zaak.identificatie}",
        f"get_zaak:{zaak.uuid}:{zaak.url}",
    ]

    for key in keys:
        cache.delete(key)
