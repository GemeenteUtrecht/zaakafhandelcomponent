from itertools import chain, groupby
from typing import Dict, List, Optional

from django.http import HttpRequest

from zac.contrib.objects.kownsl.data import ReviewRequest
from zgw.models.zrc import Zaak

from ..services import get_zaak


def get_zaak_from_query(request: HttpRequest, param: str = "zaak") -> Zaak:
    zaak_url = request.GET.get(param)
    if not zaak_url:
        raise ValueError(f"Expected '{param}' querystring parameter")

    zaak = get_zaak(zaak_url=zaak_url)
    return zaak


def get_source_doc_versions(
    review_requests: List[ReviewRequest],
) -> Optional[Dict[str, int]]:
    advices = list(chain(*[rr.advices for rr in review_requests if rr.advices]))
    all_documents = sum((advice.documents for advice in advices), [])
    sort_key = lambda ad: ad.document  # noqa
    all_documents = sorted(all_documents, key=sort_key)
    doc_versions = {
        document_url: min(doc.source_version for doc in docs)
        for document_url, docs in groupby(all_documents, key=sort_key)
    }
    return doc_versions
