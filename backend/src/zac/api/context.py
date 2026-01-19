from dataclasses import dataclass
from typing import Optional, Tuple
from uuid import UUID

from django.urls import reverse

from zgw_consumers.api_models.catalogi import ZaakType

from zac.camunda.data import Task
from zac.camunda.process_instances import get_process_instance
from zac.camunda.user_tasks import Context
from zac.core.camunda.utils import get_process_zaak_url
from zac.core.services import fetch_zaaktype, get_zaak
from zgw.models.zrc import Zaak


@dataclass
class ZaakContext(Context):
    zaak: Zaak
    documents_link: Optional[str] = ""
    zaaktype: Optional[ZaakType] = None


def get_zaak_url_from_context(
    task: Task, zaak_url_variable: str = "zaakUrl"
) -> Tuple[UUID, str]:
    process_instance = get_process_instance(task.process_instance_id)
    zaak_url = get_process_zaak_url(
        process_instance, zaak_url_variable=zaak_url_variable
    )
    return task.id, zaak_url


def get_zaak_context(
    task: Task,
    require_zaaktype: bool = False,
    zaak_url_variable: str = "zaakUrl",
) -> ZaakContext:
    task_pid, zaak_url = get_zaak_url_from_context(
        task, zaak_url_variable=zaak_url_variable
    )
    zaak = get_zaak(zaak_url=zaak_url)
    zaaktype = fetch_zaaktype(zaak.zaaktype) if require_zaaktype else None
    doc_url = reverse(
        "zaak-documents-es",
        kwargs={
            "bronorganisatie": zaak.bronorganisatie,
            "identificatie": zaak.identificatie,
        },
    )
    return ZaakContext(
        documents_link=doc_url,
        zaak=zaak,
        zaaktype=zaaktype,
    )
