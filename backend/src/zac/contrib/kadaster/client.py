import types
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urljoin

from django.conf import settings

import requests
from requests import Session
from requests.structures import CaseInsensitiveDict
from zds_client.client import ClientError
from zds_client.schema import get_headers

from zac.zgw_client import ZGWClient

Object = Dict[str, Any]


def bag_request(
    self,
    path: str,
    operation: str,
    method="GET",
    expected_status=200,
    request_kwargs: Optional[dict] = None,
    **kwargs,
) -> Union[List[Object], Object]:
    """
    Make the HTTP request using requests.

    The URL is created based on the path and base URL and any defaults
    from the OAS schema are injected.

    :return: a list or dict, the result of calling response.json()
    :raises: :class:`requests.HTTPException` for internal server errors
    :raises: :class:`ClientError` for HTTP 4xx status codes
    """
    url = urljoin(self.base_url, path)
    if request_kwargs:
        kwargs.update(request_kwargs)
    headers = CaseInsensitiveDict(kwargs.pop("headers", {}))
    headers.setdefault("Content-Type", "application/json")
    schema_headers = get_headers(self.schema, operation)
    for header, value in schema_headers.items():
        headers.setdefault(header, value)
    if self.auth:
        headers.update(self.auth.credentials())
    kwargs["headers"] = headers
    kwargs.setdefault("timeout", settings.REQUESTS_DEFAULT_TIMEOUT)

    # Use the session's request method (self is a ZGWClient/Session subclass)
    # to benefit from the retry adapter and connection pooling.
    response = Session.request(self, method, url, **kwargs)
    try:
        response_json = response.json()
    except Exception:
        response_json = None
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        if response.status_code >= 500:
            raise
        raise ClientError(response_json) from exc
    assert response.status_code == expected_status, response_json
    return response_json


def override_zds_client(client: ZGWClient):
    client.request = types.MethodType(bag_request, client)
    return client
