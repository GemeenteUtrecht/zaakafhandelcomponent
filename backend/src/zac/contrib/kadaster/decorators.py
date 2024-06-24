from functools import wraps

from django.utils.encoding import force_str

import requests
from rest_framework import status
from zds_client.client import ClientError

from .exceptions import KadasterAPIException


def catch_httperror(func: callable):
    """
    Catch requests.HTTPError and raise an APIException instead.
    """

    @wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.HTTPError as exc:
            status_code = getattr(
                exc.response, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            raise KadasterAPIException(detail=exc.args[0], status_code=status_code)

    return wrapped


def catch_bag_zdserror(func: callable):
    """
    Catch requests.HTTPError and raise an APIException instead.
    """

    @wraps(func)
    def wrapped(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ClientError as exc:
            status_code = int(
                exc.args[0].get("status", status.HTTP_500_INTERNAL_SERVER_ERROR)
            )
            code = exc.args[0].get("code", "error")
            detail = exc.args[0].get("title", force_str(exc.args[0]))
            exc = KadasterAPIException(
                detail=detail, code=code, status_code=status_code
            )
            raise exc

    return wrapped
