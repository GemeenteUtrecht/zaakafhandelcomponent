from django.urls import reverse

from .constants import DocFileTypes


def get_dowc_url(obj, purpose: str = DocFileTypes.read) -> str:
    return reverse(
        "dowc:request-doc",
        kwargs={
            "bronorganisatie": obj.bronorganisatie,
            "identificatie": obj.identificatie,
            "purpose": purpose,
        },
    )
