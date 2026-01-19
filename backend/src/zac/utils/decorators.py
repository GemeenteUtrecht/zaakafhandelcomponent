import functools
import inspect
import logging
import time
from functools import wraps

from django.core.cache import caches

import requests

logger = logging.getLogger(__name__)


import inspect
import logging
import pickle
from functools import wraps

from django.core.cache import caches

logger = logging.getLogger(__name__)


def cache(key: str, alias: str = "default", **set_options):
    """
    Cache decorator that safely caches function results using a formatted key.

    - Keeps your dynamic key templating logic intact.
    - Adds graceful handling for unpicklable objects (e.g. lxml.etree._Element).
    - Supports skip_cache=True kwarg to bypass caching.
    """

    def decorator(func: callable):
        argspec = inspect.getfullargspec(func)

        if argspec.defaults:
            positional_count = len(argspec.args) - len(argspec.defaults)
            defaults = dict(zip(argspec.args[positional_count:], argspec.defaults))
        else:
            defaults = {}

        @wraps(func)
        def wrapped(*args, **kwargs):
            skip_cache = kwargs.pop("skip_cache", False)
            if skip_cache:
                return func(*args, **kwargs)

            key_kwargs = defaults.copy()
            named_args = dict(zip(argspec.args, args), **kwargs)
            key_kwargs.update(**named_args)

            if argspec.varkw:
                var_kwargs = {
                    key: value
                    for key, value in named_args.items()
                    if key not in argspec.args
                }
                key_kwargs[argspec.varkw] = var_kwargs

            cache_key = key.format(**key_kwargs)
            _cache = caches[alias]

            # Try to fetch from cache
            result = _cache.get(cache_key)
            if result is not None:
                logger.debug("Cache key '%s' hit", cache_key)
                return result

            # Compute the function result
            result = func(*args, **kwargs)

            # Attempt to cache it safely
            try:
                # Ensure picklable before caching
                pickle.dumps(result)
                _cache.set(cache_key, result, **set_options)
                logger.debug("Cache key '%s' stored successfully", cache_key)
            except Exception as e:
                logger.debug(
                    "Skipping cache for key '%s': object of type %s is unpicklable (%s)",
                    cache_key,
                    type(result).__name__,
                    e,
                )

            return result

        return wrapped

    return decorator


def optional_service(func: callable):
    """
    Mark the callable as external-service consumer with a non-essential service.

    If the service is down or in error state, this won't break our own application.
    Useful as a development tool to not require peripheral systems to be running as
    well.
    """

    ret_type = inspect.getfullargspec(func).annotations["return"]

    is_optional = (
        hasattr(ret_type, "__args__")
        and len(ret_type.__args__) == 2  # noqa
        and ret_type.__args__[-1] is type(None)  # noqa
    )

    # .__origin__() is... tricky
    default = None if (is_optional or ret_type is None) else ret_type.__origin__()

    # figure out the default value from the type hint
    def decorator(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.ConnectionError as exc:
            logger.debug("Service(s) down (%s)", exc.request.url)
            return default

    return decorator


def retry(
    times=3,
    exceptions=(Exception,),
    condition: callable = lambda exc: True,
    delay=1.0,
    on_failure: callable = lambda exc, *args, **kwargs: None,
):
    """
    Retry the decorated callable up to ``times`` if it raises a known exception.

    If the retries are all spent, then on_failure will be invoked.

    # Taken from bptl.utils.decorators
    # https://github.com/GemeenteUtrecht/bptl/blob/master/src/bptl/utils/decorators.py
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            tries_left = times + 1

            logger.info("Tries left: %d, %r", tries_left, func)

            while tries_left > 0:
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    # the extra exception check doesn't pass, so consider it an
                    # unexpected exception
                    if not condition(exc):
                        raise
                    else:  # expected exception, retry (if there are retries left)
                        tries_left -= 1

                    # if we've reached the maximum number of retries, raise the
                    # exception again
                    if tries_left < 1:
                        logger.error("Task didn't succeed after %d retries", times)
                        on_failure(exc, *args, **kwargs)
                        raise

                time.sleep(delay)

        return wrapper

    return decorator
