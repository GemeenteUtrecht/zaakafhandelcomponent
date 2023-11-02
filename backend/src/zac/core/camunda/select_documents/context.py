from zac.camunda.data import Task
from zac.camunda.user_tasks import register
from zac.core.camunda.utils import get_process_zaak_url
from zac.core.services import get_informatieobjecttypen_for_zaaktype, get_zaak
from zac.elasticsearch.searches import get_documenten_es

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
    documenten = get_documenten_es(zaak)

    bijdrage_zaak_url = get_process_zaak_url(task, zaak_url_variable="zaakUrl")
    bijdrage_zaak = get_zaak(zaak_url=bijdrage_zaak_url)
    bijdrage_zaak_document_titels = [
        doc.titel for doc in get_documenten_es(bijdrage_zaak)
    ]
    documenten = [
        doc for doc in documenten if doc.titel not in bijdrage_zaak_document_titels
    ]

    related_zaaktype = get_zaaktype_from_identificatie(task)
    informatieobjecttypen = get_informatieobjecttypen_for_zaaktype(related_zaaktype)
    return DocumentSelectContext(
        documents=documenten, informatieobjecttypen=informatieobjecttypen
    )
