from typing import Dict

from django.utils.translation import gettext_lazy as _

from zac.api.context import get_zaak_context
from zac.camunda.data import Task
from zac.camunda.user_tasks import register

from .serializers import (
    CamundaZaakProcessContextSerializer,
    ConfigureZaakProcessSerializer,
    get_required_process_informatie_objecten,
)
from .utils import (
    get_camunda_start_process_from_zaakcontext,
    get_required_rollen,
    get_required_zaakeigenschappen,
)


@register(
    "zac:StartProcessForm",
    CamundaZaakProcessContextSerializer,
    ConfigureZaakProcessSerializer,
)
def get_zaak_start_process_form_context(task: Task) -> Dict:
    zaak_context = get_zaak_context(task, require_zaaktype=True, require_documents=True)
    camunda_start_process = get_camunda_start_process_from_zaakcontext(zaak_context)
    informatieobjecten = get_required_process_informatie_objecten(
        zaak_context, camunda_start_process
    )
    rollen = get_required_rollen(zaak_context, camunda_start_process)
    zaakeigenschappen = get_required_zaakeigenschappen(
        zaak_context, camunda_start_process
    )
    return {
        "zaakeigenschappen": zaakeigenschappen,
        "informatieobjecten": informatieobjecten,
        "rollen": rollen,
    }
