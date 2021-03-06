from dataclasses import dataclass
from typing import List, Optional

from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.api_models.documenten import Document

from zac.camunda.data import Task
from zac.camunda.process_instances import get_process_instance
from zac.camunda.user_tasks import Context
from zac.core.camunda import get_process_zaak_url
from zac.core.services import fetch_zaaktype, get_documenten, get_zaak
from zgw.models.zrc import Zaak


@dataclass
class ZaakContext(Context):
    zaak: Zaak
    documents: Optional[List[Document]] = None
    zaaktype: Optional[ZaakType] = None


def get_zaak_context(
    task: Task, require_zaaktype: bool = False, require_documents: bool = False
) -> ZaakContext:
    process_instance = get_process_instance(task.process_instance_id)
    zaak_url = get_process_zaak_url(process_instance)
    zaak = get_zaak(zaak_url=zaak_url)
    zaaktype = fetch_zaaktype(zaak.zaaktype) if require_zaaktype else None
    docs_context = get_documenten(zaak) if require_documents else (None, None)
    return ZaakContext(
        documents=docs_context[0],
        zaak=zaak,
        zaaktype=zaaktype,
    )
