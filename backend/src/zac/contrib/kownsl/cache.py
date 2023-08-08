from typing import Dict

from django.core.cache import cache

from zac.core.services import get_zaak


def invalidate_review_requests_cache(rr: Dict):
    zaak = get_zaak(rr["forZaak"])
    keys = [
        f"reviewrequests:zaak:{zaak.id}",
        f"reviewrequest:advices:{rr['id']}",
        f"reviewrequest:approvals:{rr['id']}",
        f"reviewrequest:detail:{rr['id']}",
    ]
    cache.delete_many(keys)
