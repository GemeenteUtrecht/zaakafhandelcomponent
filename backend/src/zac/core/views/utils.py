from itertools import chain, groupby
from typing import Dict, List, Optional

from django.http import HttpRequest

from zgw_consumers.api_models.documenten import Document
from zgw_consumers.api_models.zaken import Zaak

from zac.accounts.models import User
from zac.contrib.kownsl.data import ReviewRequest

from ..permissions import zaken_download_documents
from ..services import get_zaak


def get_zaak_from_query(request: HttpRequest, param: str = "zaak") -> Zaak:
    zaak_url = request.GET.get(param)
    if not zaak_url:
        raise ValueError(f"Expected '{param}' querystring parameter")

    zaak = get_zaak(zaak_url=zaak_url)
    return zaak


def filter_documenten_for_permissions(
    documenten: List[Document],
    user: User,
) -> List[Document]:
    """Filter documents on the user permissions. """

    filtered_documents = []
    for document in documenten:
        if user.has_perm(zaken_download_documents.name, document):
            filtered_documents.append(document)
    return filtered_documents


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
