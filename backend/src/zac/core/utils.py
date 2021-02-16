from typing import List, Optional
from urllib.parse import urlencode, urljoin

from django.conf import settings
from django.http import HttpRequest
from django.urls import get_script_prefix


def get_ui_url(paths: List[str], params: Optional[dict] = {}) -> str:
    """"""
    root = get_script_prefix()

    url = urljoin(root, "/".join(paths))

    if params:
        params = "?" + urlencode(params)
        url = urljoin(url, params)

    return url


def build_absolute_url(path: str, request: Optional[HttpRequest] = None) -> str:
    from django.contrib.sites.models import Site

    if request is not None:
        return request.build_absolute_uri(path)

    domain = Site.objects.get_current().domain
    protocol = "https" if settings.IS_HTTPS else "http"
    return f"{protocol}://{domain}{path}"
