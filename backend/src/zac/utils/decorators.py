import functools
import inspect
import logging
import pickle
import time
from functools import wraps

from django.core.cache import caches

import requests

logger = logging.getLogger(__name__)

_STALE_SUFFIX = ":stale"
_DEFAULT_STALE_TTL_MULTIPLIER = 10


class CircuitOpenError(Exception):
    """Raised when a service circuit breaker is open."""

    def __init__(self, service_name: str):
        self.service_name = service_name
        super().__init__(f"Circuit breaker open for '{service_name}': refusing call.")


def _record_failure(
    cache_backend, cb_name, failure_window, failure_threshold, recovery_timeout
):
    """Record a failure and trip the circuit if threshold is exceeded."""
    failures_key = f"cb:{cb_name}:failures"
    open_key = f"cb:{cb_name}:open"
    try:
        try:
            new_count = cache_backend.incr(failures_key)
        except ValueError:
            cache_backend.set(failures_key, 1, failure_window)
            new_count = 1

        if new_count >= failure_threshold:
            cache_backend.set(open_key, 1, recovery_timeout)
            logger.warning(
                "Circuit breaker OPEN for '%s' after %d failures in %ds.",
                cb_name,
                new_count,
                failure_window,
            )
    except Exception:
        pass  # Redis unavailable — fail open


def _reset_circuit(cache_backend, cb_name):
    """Reset circuit breaker state after a successful call."""
    try:
        cache_backend.delete(f"cb:{cb_name}:failures")
        cache_backend.delete(f"cb:{cb_name}:open")
    except Exception:
        pass


def _is_circuit_open(cache_backend, cb_name):
    """Check if the circuit is currently open."""
    try:
        return cache_backend.get(f"cb:{cb_name}:open") is not None
    except Exception:
        return False  # Redis unavailable — fail open


def cache(key: str, alias: str = "default", stale_ttl: int = None, **set_options):
    """
    Cache decorator that safely caches function results using a formatted key.

    - Keeps your dynamic key templating logic intact.
    - Adds graceful handling for unpicklable objects (e.g. lxml.etree._Element).
    - Supports skip_cache=True kwarg to bypass caching.
    - Stale-while-error: on failure, serves previously cached data from a
      shadow key with a longer TTL.
    - Circuit breaker: short-circuits calls to services that have failed
      repeatedly, serving stale data or raising CircuitOpenError.
    """

    def decorator(func: callable):
        argspec = inspect.getfullargspec(func)

        if argspec.defaults:
            positional_count = len(argspec.args) - len(argspec.defaults)
            defaults = dict(zip(argspec.args[positional_count:], argspec.defaults))
        else:
            defaults = {}

        # Compute stale TTL: explicit > 10x normal timeout > None (disabled)
        _stale_ttl = stale_ttl
        if _stale_ttl is None and "timeout" in set_options:
            _stale_ttl = set_options["timeout"] * _DEFAULT_STALE_TTL_MULTIPLIER

        # Circuit breaker identity
        cb_name = func.__qualname__

        @wraps(func)
        def wrapped(*args, **kwargs):
            from django.conf import settings

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
            stale_key = cache_key + _STALE_SUFFIX
            _cache = caches[alias]

            # --- Primary cache hit ---
            result = _cache.get(cache_key)
            if result is not None:
                logger.debug("Cache key '%s' hit", cache_key)
                return result

            # --- Circuit breaker check ---
            cb_threshold = getattr(settings, "CB_FAILURE_THRESHOLD", 5)
            cb_window = getattr(settings, "CB_FAILURE_WINDOW", 60)
            cb_recovery = getattr(settings, "CB_RECOVERY_TIMEOUT", 30)

            if _is_circuit_open(_cache, cb_name):
                if _stale_ttl is not None:
                    stale = _cache.get(stale_key)
                    if stale is not None:
                        logger.warning(
                            "Circuit open for '%s', serving stale data for key '%s'.",
                            cb_name,
                            cache_key,
                        )
                        return stale
                raise CircuitOpenError(cb_name)

            # --- Primary cache miss: call the function ---
            try:
                result = func(*args, **kwargs)
            except Exception as exc:
                _record_failure(_cache, cb_name, cb_window, cb_threshold, cb_recovery)

                # Stale-while-error fallback
                if _stale_ttl is not None:
                    stale = _cache.get(stale_key)
                    if stale is not None:
                        logger.warning(
                            "Service call failed for '%s', serving stale data. Error: %s",
                            cache_key,
                            exc,
                        )
                        return stale
                raise

            # --- Success: store result and reset circuit ---
            _reset_circuit(_cache, cb_name)

            try:
                pickle.dumps(result)
                _cache.set(cache_key, result, **set_options)
                if _stale_ttl is not None:
                    _cache.set(stale_key, result, _stale_ttl)
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
