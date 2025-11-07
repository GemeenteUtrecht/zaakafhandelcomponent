"""
Replace the OAS schema cache with django's cache mechanism.
"""

from django.core.cache import caches

from zds_client.oas import schema_fetcher


class OASCache:
    KEY_PREFIX = "oas"
    DURATION = 60 * 60 * 24  # 24 hours

    def __init__(self):
        self._local_cache = {}  # in memory

    def __contains__(self, key: str):
        key = f"{self.KEY_PREFIX}:{key}"
        if key in self._local_cache:
            return True
        else:
            schema = caches["oas"].get(key)
            if schema is None:
                return False

            self._local_cache[key] = schema
            return True

    def __getitem__(self, key: str):
        key = f"{self.KEY_PREFIX}:{key}"
        if key in self._local_cache:
            return self._local_cache[key]

    def __setitem__(self, key: str, value: dict):
        key = f"{self.KEY_PREFIX}:{key}"
        caches["oas"].set(key, value, self.DURATION)
        self._local_cache[key] = value


def replace_cache():
    schema_fetcher.cache = OASCache()
