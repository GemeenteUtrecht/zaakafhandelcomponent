from typing import Dict, List, Optional
from urllib.parse import urlencode, urljoin

from django.conf import settings
from django.http import HttpRequest
from django.urls import get_script_prefix

from zgw_consumers.concurrent import parallel
from zgw_consumers.models import Service

from zac.client import Client
from zac.core.models import CoreConfig
from zac.utils.decorators import cache

A_DAY = 60 * 60 * 24


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


@cache("object:{url}", timeout=A_DAY)
def _fetch_object(client: Client, url: str) -> dict:
    retrieved_item = client.retrieve("object", url=url)
    service = Service.get_service(retrieved_item["type"])

    if not service:
        raise RuntimeError("No service for the objecttype API has been configured.")

    objecttype_client = service.build_client()
    objecttype = objecttype_client.retrieve("objecttype", url=retrieved_item["type"])

    retrieved_item["type"] = objecttype
    return retrieved_item


def fetch_objects(urls: List[str]) -> List[Dict]:
    config = CoreConfig.get_solo()
    object_api = config.primary_objects_api
    if not object_api:
        raise RuntimeError("No objects API has been configured yet.")
    object_api_client = object_api.build_client()

    def fetch_object(url):
        return _fetch_object(object_api_client, url)

    with parallel() as executor:
        retrieved_objects = list(executor.map(fetch_object, urls))

    return retrieved_objects
