from typing import List

from django.http import HttpRequest

from zgw_consumers.api_models.documenten import Document
from zgw_consumers.api_models.zaken import Zaak

from zac.accounts.models import User

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
