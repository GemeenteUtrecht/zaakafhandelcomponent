from django.core.cache import cache

from zgw.models.zrc import Zaak


def invalidate_cache_fetch_checklist_object(zaak: Zaak):
    cache.delete(f"fetch_checklist_object:{zaak.url}")
