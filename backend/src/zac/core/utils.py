from typing import Dict, List, Optional, Union

from django.conf import settings
from django.http import HttpRequest

from furl import furl

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
