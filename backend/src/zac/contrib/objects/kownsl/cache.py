from django.core.cache import cache

from zgw.models.zrc import Zaak

from .data import ReviewRequest


def invalidate_review_requests_cache(rr: ReviewRequest):
    zaak_uuid = (
        rr.zaak.uuid
        if isinstance(rr.zaak, Zaak)
        else [seg for seg in rr.zaak.split("/") if seg][-1]
    )
    keys = [
        f"review_requests:zaak:{zaak_uuid}",
        f"review_request:detail:{rr.id}",
    ]
    cache.delete_many(keys)


def invalidate_review_cache(rr: ReviewRequest):
    zaak_uuid = (
        rr.zaak.uuid
        if isinstance(rr.zaak, Zaak)
        else [seg for seg in rr.zaak.split("/") if seg][-1]
    )
    keys = [
        f"reviews:zaak:{zaak_uuid}",
        f"reviews:review_request:{rr.id}",
    ]
    cache.delete_many(keys)
