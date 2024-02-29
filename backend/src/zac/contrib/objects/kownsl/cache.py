from django.core.cache import cache

from zac.core.services import get_zaak
from zgw.models.zrc import Zaak

from .data import ReviewRequest


def invalidate_review_requests_cache(rr: ReviewRequest):
    zaak = rr.zaak if isinstance(rr.zaak, Zaak) else get_zaak(zaak_url=rr.zaak)

    keys = [
        f"review_requests:zaak:{zaak.uuid}",
        f"review_request:detail:{rr.id}",
    ]
    cache.delete_many(keys)


def invalidate_review_cache(rr: ReviewRequest):
    zaak = rr.zaak if isinstance(rr.zaak, Zaak) else get_zaak(zaak_url=rr.zaak)
    keys = [
        f"reviews:zaak:{zaak.uuid}",
        f"reviews:review_request:{rr.id}",
        f"reviews:requester:{rr.requester['username']}",
    ]
    cache.delete_many(keys)
