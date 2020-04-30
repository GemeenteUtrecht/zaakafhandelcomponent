from django.core.cache import caches


class ClearCachesMixin:
    def setUp(self):
        super().setUp()

        for cache in caches.all():
            cache.clear()
            self.addCleanup(cache.clear)
