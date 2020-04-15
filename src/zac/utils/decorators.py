import inspect
import logging
from functools import wraps

from django.core.cache import caches

logger = logging.getLogger(__name__)


def cache(key: str, alias: str = "default", **set_options):
    def decorator(func: callable):
        argspec = inspect.getfullargspec(func)

        if argspec.defaults:
            positional_count = len(argspec.args) - len(argspec.defaults)
            defaults = dict(zip(argspec.args[positional_count:], argspec.defaults))
        else:
            defaults = {}

        @wraps(func)
        def wrapped(*args, **kwargs):
            key_kwargs = defaults.copy()
            named_args = dict(zip(argspec.args, args), **kwargs)
            key_kwargs.update(**named_args)

            cache_key = key.format(**key_kwargs)

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
