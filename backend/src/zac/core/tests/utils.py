from django.core.cache import cache, caches

from zds_client.oas import schema_fetcher
from zgw_consumers.concurrent import parallel


class mock_parallel(parallel):
    def map(self, fn, *iterables, timeout=None, chunksize=1):
        return map(fn, *iterables)


class ClearCachesMixin:
    def setUp(self):
        super().setUp()

        for _cache in caches.all():
            _cache.clear()
            self.addCleanup(_cache.clear)
        cache.clear()
        schema_fetcher.cache._local_cache = {}
