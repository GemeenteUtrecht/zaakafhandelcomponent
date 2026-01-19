import logging
from os import path

from django.urls import reverse

from zgw_consumers.api_models.documenten import Document

from zac.elasticsearch.searches import search_informatieobjects

from .api import get_supported_extensions
from .constants import DocFileTypes

logger = logging.getLogger(__name__)


def get_dowc_url_from_obj(obj: Document, purpose: str = DocFileTypes.read) -> str:
    fn, fext = path.splitext(obj.bestandsnaam)
    if fext not in get_supported_extensions() and purpose != DocFileTypes.download:
        return ""

    return reverse(
        "dowc:request-doc",
        kwargs={
            "bronorganisatie": obj.bronorganisatie,
            "identificatie": obj.identificatie,
            "purpose": purpose,
        },
    )


def get_dowc_url_from_vars(
    bronorganisatie: str, identificatie: str, purpose: str = DocFileTypes.read
) -> str:

    results = search_informatieobjects(
        bronorganisatie=bronorganisatie, identificatie=identificatie, size=1
    )
    if not results:
        logger.warning(
            "Could not find a document with bronorganisatie {bron} and identificatie {id}.".format(
                bron=bronorganisatie, id=identificatie
            )
        )

    return get_dowc_url_from_obj(results[0], purpose=purpose)
