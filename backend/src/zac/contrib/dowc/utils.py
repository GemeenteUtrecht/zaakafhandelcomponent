from django.urls import reverse

from zgw_consumers.api_models.documenten import Document

from .constants import DocFileTypes


def get_dowc_url_from_obj(obj: Document, purpose: str = DocFileTypes.read) -> str:
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
    return reverse(
        "dowc:request-doc",
        kwargs={
            "bronorganisatie": bronorganisatie,
            "identificatie": identificatie,
            "purpose": purpose,
        },
    )
