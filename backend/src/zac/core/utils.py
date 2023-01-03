from typing import Dict, List, Optional, Union

from django.conf import settings
from django.http import HttpRequest

from furl import furl
from zgw_consumers.concurrent import parallel
from zgw_consumers.models import Service

from zac.client import Client
from zac.core.models import CoreConfig
from zac.utils.decorators import cache

AN_HOUR = 60 * 60
A_DAY = AN_HOUR * 24


def build_absolute_url(
    path: Union[List[str], str],
    request: Optional[HttpRequest] = None,
    params: Optional[Dict[str, str]] = None,
) -> str:
    if request is not None:
        if type(path) == list:
            path = furl(path=path)
            path.path.isabsolute = True
            path = path.url
        return request.build_absolute_uri(path)

    from django.contrib.sites.models import Site

    domain = Site.objects.get_current().domain
    if not domain.startswith("http"):
        domain = f'{"https://" if settings.IS_HTTPS else "http://"}{domain}'

    domain = furl(domain)
    if type(path) == str:
        path = furl(path)
        domain.path.segments += path.path.segments
        domain.args.update(path.args)

    elif type(path) == list:
        domain.path.segments += path

    domain.path.normalize()

    if params:
        domain.args.update(params)

    return domain.url


@cache("objecttype:{url}", timeout=AN_HOUR)
def _fetch_objecttype(client: Client, url: str) -> dict:
    object_type = client.retrieve("objecttype", url=url)

    # get the versions, expanded
    objecttype_versions = client.list(
        "objectversion", objecttype_uuid=object_type["uuid"]
    )
    object_type["versions"] = objecttype_versions

    return object_type


@cache("object:{url}", timeout=A_DAY)
def fetch_object(client: Client, url: str) -> dict:
    retrieved_item = client.retrieve("object", url=url)
    service = Service.get_service(retrieved_item["type"])

    if not service:
        raise RuntimeError("No service for the objecttype API has been configured.")

    objecttype_client = service.build_client()
    retrieved_item["type"] = _fetch_objecttype(
        objecttype_client, url=retrieved_item["type"]
    )
    return retrieved_item


def fetch_objects(urls: List[str]) -> List[Dict]:
    config = CoreConfig.get_solo()
    object_api = config.primary_objects_api
    if not object_api:
        raise RuntimeError("No objects API has been configured yet.")
    object_api_client = object_api.build_client()

    def _fetch_object(url):
        return fetch_object(object_api_client, url)

    with parallel() as executor:
        retrieved_objects = list(executor.map(_fetch_object, urls))

    return retrieved_objects
