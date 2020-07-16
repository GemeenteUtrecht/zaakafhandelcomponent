"""
Wrap around concurrent.futures to add Django-specific cleanup behaviour.
"""
from concurrent import futures

from django.db import close_old_connections


class parallel:
    def __init__(self, **kwargs):
        self.executor = futures.ThreadPoolExecutor(**kwargs)

    def submit(*args, **kwargs):
        if len(args) >= 2:
            self, _fn, *args = args
        elif "fn" in kwargs:
            _fn = kwargs.pop("fn")
            self, *args = args

        # wrap the callable so that db connections are closed afterwards
        def fn(*fn_args, **fn_kwargs):
            result = _fn(*fn_args, **fn_kwargs)
            close_old_connections()
            return result

        return self.executor.submit(fn, *args, **kwargs)

    def map(self, fn, *iterables, timeout=None, chunksize=1):
        return self.executor.map(fn, *iterables, timeout=timeout, chunksize=chunksize)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return self.executor.__exit__(exc_type, exc_val, exc_tb)
