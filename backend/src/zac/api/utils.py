from typing import List

from django.conf import settings
from django.contrib.sites.models import Site

from furl import furl


def remote_schema_ref(url: str, fragment_parts: List[str]) -> dict:
    ref = furl(Site.objects.get(id=settings.SITE_ID).domain)
    ref.path.segments = ["api", "_get-remote-schema", ""]
    ref.path.normalize()
    ref.args["schema"] = url
    ref.fragment.path.segments = fragment_parts
    ref.fragment.path.isabsolute = True
    return {"$ref": ref.url}
