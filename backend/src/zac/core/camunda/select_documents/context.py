from zac.api.context import get_zaak_context
from zac.camunda.data import Task
from zac.camunda.user_tasks import register

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
    return DocumentSelectContext(documents=zaak_context.documents)
