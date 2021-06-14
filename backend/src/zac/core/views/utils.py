from itertools import chain, groupby
from typing import Dict, List, Optional

from django.http import HttpRequest

from rest_framework.permissions import SAFE_METHODS
from rest_framework.request import Request
from zgw_consumers.api_models.documenten import Document

from zac.contrib.kownsl.data import ReviewRequest
from zgw.models.zrc import Zaak

from ..permissions import zaken_download_documents, zaken_update_documents
from ..services import get_zaak


def get_zaak_from_query(request: HttpRequest, param: str = "zaak") -> Zaak:
    zaak_url = request.GET.get(param)
    if not zaak_url:
        raise ValueError(f"Expected '{param}' querystring parameter")

    zaak = get_zaak(zaak_url=zaak_url)
    return zaak


def filter_documenten_for_permissions(
    documenten: List[Document],
    request: Request,
) -> List[Document]:
    """Filter documents on the user permissions."""

    if request.method in SAFE_METHODS:
        permission = zaken_download_documents
    else:
        permission = zaken_update_documents

    filtered_documents = []
    for document in documenten:
        if request.user.has_perm(permission.name, document):
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
