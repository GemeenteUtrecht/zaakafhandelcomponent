from django.core.cache import cache

from zgw.models.zrc import Zaak


def invalidate_cache_fetch_oudbehandelaren(zaak: Zaak):
    cache.delete(f"fetch_oudbehandelaren_object:{zaak.url}")
