from zac.camunda.data import Task
from zac.camunda.process_instances import get_process_instance
from zac.camunda.user_tasks import register
from zac.core.services import (
    fetch_zaaktype,
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


@register(
    "zac:documentSelectie",
    DocumentSelectContextSerializer,
    DocumentSelectTaskSerializer,
)
def get_context(task: Task) -> DocumentSelectContext:
    process_instance = get_process_instance(task.process_instance_id)

    zaak_url = process_instance.get_variable("hoofdZaakUrl")
    zaak = get_zaak(zaak_url=zaak_url)
    documenten, gone = get_documenten(zaak)
    resolved_documenten = resolve_documenten_informatieobjecttypen(documenten)

    related_zaaktype_url = process_instance.get_variable("zaaktype")
    related_zaaktype = fetch_zaaktype(related_zaaktype_url)
    informatieobjecttypen = get_informatieobjecttypen_for_zaaktype(related_zaaktype)

    return DocumentSelectContext(
        documents=resolved_documenten, informatieobjecttypen=informatieobjecttypen
    )
