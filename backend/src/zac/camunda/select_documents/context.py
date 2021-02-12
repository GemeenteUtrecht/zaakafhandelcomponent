from typing import List

from zgw_consumers.api_models.documenten import Document

from zac.camunda.data import Task
from zac.camunda.process_instances import get_process_instance
from zac.camunda.user_tasks import register
from zac.core.camunda import get_process_zaak_url
from zac.core.services import get_documenten, get_zaak

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
def get_context(task: Task) -> List[Document]:
    process_instance = get_process_instance(task.process_instance_id)
    zaak_url = get_process_zaak_url(process_instance)
    zaak = get_zaak(zaak_url=zaak_url)
    documents, rest = get_documenten(zaak)
    return DocumentSelectContext(documents=documents)
