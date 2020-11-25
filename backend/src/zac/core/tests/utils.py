from django.core.cache import caches

from zds_client.oas import schema_fetcher


class ClearCachesMixin:
    def setUp(self):
        super().setUp()

        for cache in caches.all():
            cache.clear()
            self.addCleanup(cache.clear)

        schema_fetcher.cache._local_cache = {}
