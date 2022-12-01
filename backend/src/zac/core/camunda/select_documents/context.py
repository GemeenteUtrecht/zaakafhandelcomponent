from zac.camunda.data import Task
from zac.camunda.user_tasks import register
from zac.core.camunda.utils import get_process_zaak_url
from zac.core.services import (
    get_documenten,
    get_informatieobjecttypen_for_zaaktype,
    get_zaak,
    resolve_documenten_informatieobjecttypen,
)

from .serializers import (
    DocumentSelectContext,
    DocumentSelectContextSerializer,
    DocumentSelectTaskSerializer,
)
from .utils import get_zaaktype_from_identificatie


@register(
    "zac:documentSelectie",
    DocumentSelectContextSerializer,
    DocumentSelectTaskSerializer,
)
def get_context(task: Task) -> DocumentSelectContext:
    zaak_url = get_process_zaak_url(task, zaak_url_variable="hoofdZaakUrl")
    zaak = get_zaak(zaak_url=zaak_url)
    documenten, gone = get_documenten(zaak)

    bijdrage_zaak_url = get_process_zaak_url(task, zaak_url_variable="zaakUrl")
    bijdrage_zaak = get_zaak(zaak_url=bijdrage_zaak_url)
    bijdrage_zaak_document_urls = [
        doc.titel for doc in get_documenten(bijdrage_zaak)[0]
    ]
    documenten = [
        doc for doc in documenten if doc.titel not in bijdrage_zaak_document_urls
    ]

    resolved_documenten = resolve_documenten_informatieobjecttypen(documenten)
    related_zaaktype = get_zaaktype_from_identificatie(task)
    informatieobjecttypen = get_informatieobjecttypen_for_zaaktype(related_zaaktype)
    return DocumentSelectContext(
        documents=resolved_documenten, informatieobjecttypen=informatieobjecttypen
    )
