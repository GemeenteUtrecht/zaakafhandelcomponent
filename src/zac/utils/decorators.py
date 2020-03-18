import inspect
import logging
from functools import wraps

from django.core.cache import caches

logger = logging.getLogger(__name__)


def cache(key: str, alias: str = "default", **set_options):
    def decorator(func: callable):
        argspec = inspect.getfullargspec(func)

        @wraps(func)
        def wrapped(*args, **kwargs):
            named_args = dict(zip(argspec.args, args), **kwargs)
            cache_key = key.format(**named_args)

            _cache = caches[alias]
            result = _cache.get(cache_key)
            if result is not None:
                logger.debug("Cache key '%s' hit", cache_key)
                return result

            result = func(*args, **kwargs)
            _cache.set(cache_key, result, **set_options)
            return result

        return wrapped

    return decorator
