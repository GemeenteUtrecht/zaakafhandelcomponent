import logging
from typing import List

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist
from django.db.utils import ProgrammingError

from furl import furl

logger = logging.getLogger(__name__)


def get_domain():
    try:
        site = Site.objects.get(id=settings.SITE_ID)
        return site.domain
    except ProgrammingError:
        logger.warning(
            "Could not find the sites table in the database. Please run migrate."
        )
    except ObjectDoesNotExist:
        logger.warning(
            "Could not find a registered site in the database. Please set site settings."
        )
    return ""


def remote_schema_ref(url: str, fragment_parts: List[str]) -> dict:
    ref = furl(get_domain())
    ref.path.segments += ["api", "_get-remote-schema"]
    ref.path.normalize()
    ref.args["schema"] = url
    ref.fragment.path.segments = fragment_parts
    ref.fragment.path.isabsolute = True
    return {"$ref": ""}  # ref.url}
