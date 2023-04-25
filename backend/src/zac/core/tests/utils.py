from django.core.cache import caches

from zds_client.oas import schema_fetcher


class ClearCachesMixin:
    def setUp(self):
        super().setUp()

        for _cache in caches.all():
            _cache.clear()
            self.addCleanup(_cache.clear)

        schema_fetcher.cache._local_cache = {}
