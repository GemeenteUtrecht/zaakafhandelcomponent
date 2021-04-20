from zac.api.context import get_zaak_context
from zac.camunda.data import Task
from zac.camunda.process_instances import get_process_instance
from zac.camunda.user_tasks import register
from zac.core.services import fetch_zaaktype, get_informatieobjecttypen_for_zaaktype

from .serializers import (
    DocumentSelectContext,
    DocumentSelectContextSerializer,
    DocumentSelectTaskSerializer,
)


@register(
    "zac:documentSelectie",
    DocumentSelectContextSerializer,
    DocumentSelectTaskSerializer,
)
def get_context(task: Task) -> DocumentSelectContext:
    zaak_context = get_zaak_context(task, require_documents=True)
    process_instance = get_process_instance(task.process_instance_id)
    related_zaaktype_url = process_instance.get_variable("zaaktype")
    related_zaaktype = fetch_zaaktype(related_zaaktype_url)
    informatieobjecttypen = get_informatieobjecttypen_for_zaaktype(related_zaaktype)
    return DocumentSelectContext(
        documents=zaak_context.documents, informatieobjecttypen=informatieobjecttypen
    )
