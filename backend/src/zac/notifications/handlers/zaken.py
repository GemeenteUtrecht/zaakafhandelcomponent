import logging
from typing import Any, Callable, Dict, Tuple

from django.conf import settings

from django_camunda.api import complete_task
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.constants import RolOmschrijving
from zgw_consumers.api_models.zaken import Status

from zac.accounts.models import AccessRequest
from zac.accounts.permission_loaders import add_permission_for_behandelaar
from zac.activities.constants import ActivityStatuses
from zac.activities.models import Activity
from zac.camunda.user_tasks.api import get_camunda_user_tasks
from zac.contrib.board.models import BoardItem
from zac.contrib.dowc.api import bulk_close_all_documents_for_zaak
from zac.contrib.objects.services import (
    bulk_lock_review_requests_for_zaak,
    lock_checklist_for_zaak,
)
from zac.core.cache import (
    invalidate_rollen_cache,
    invalidate_zaak_cache,
    invalidate_zaak_list_cache,
    invalidate_zaakeigenschappen_cache,
    invalidate_zaakobjecten_cache,
)
from zac.core.services import (
    client_from_url,
    fetch_rol,
    fetch_zaak_informatieobject,
    fetch_zaakobject,
    get_document,
    get_statustype,
    update_medewerker_identificatie_rol,
)
from zac.elasticsearch.api import (
    create_status_document,
    create_zaak_document,
    create_zaakinformatieobject_document,
    create_zaakobject_document,
    create_zaaktype_document,
    delete_zaak_document,
    get_zaakinformatieobject_document,
    get_zaakobject_document,
    update_eigenschappen_in_zaak_document,
    update_related_zaken_in_informatieobject_document,
    update_related_zaken_in_object_document,
    update_rollen_in_zaak_document,
    update_status_in_zaak_document,
    update_zaak_document,
    update_zaakinformatieobject_document,
)

from .utils import (
    retrieve_zaak,
    soft_update_related_zaak_in_docs,
    soft_update_related_zaak_in_objects,
)

logger = logging.getLogger(__name__)
Notification = Dict[str, Any]


class ZakenHandler:
    """Handlers for kanaal='zaken'."""

    def __init__(self) -> None:
        self._dispatch: Dict[Tuple[str, str], Callable[[Notification], None]] = {
            ("zaak", "create"): self._on_zaak_create,
            ("zaak", "update"): self._on_zaak_update,
            ("zaak", "partial_update"): self._on_zaak_update,
            ("zaak", "destroy"): self._on_zaak_destroy,
            ("zaakeigenschap", "create"): self._on_zaakeigenschap_change,
            ("zaakeigenschap", "update"): self._on_zaakeigenschap_change,
            ("zaakeigenschap", "partial_update"): self._on_zaakeigenschap_change,
            ("zaakeigenschap", "destroy"): self._on_zaakeigenschap_change,
            ("status", "create"): self._on_status_create,
            ("resultaat", "create"): self._on_resultaat_create,
            ("rol", "create"): self._on_rol_create,
            ("rol", "destroy"): self._on_rol_destroy,
            ("zaakobject", "create"): self._on_zaakobject_create,
            ("zaakobject", "destroy"): self._on_zaakobject_destroy,
            ("zaakinformatieobject", "create"): self._on_zaakinformatieobject_create,
            ("zaakinformatieobject", "update"): self._on_zaakinformatieobject_update,
            ("zaakinformatieobject", "destroy"): self._on_zaakinformatieobject_destroy,
        }

    def handle(self, data: Notification) -> None:
        logger.debug("ZAC notification: %r", data)
        key = (data.get("resource"), data.get("actie"))
        handler = self._dispatch.get(key)
        if handler:
            handler(data)
        else:
            logger.debug("No zaken handler for %s", key)

    # ---- Zaak ----
    def _on_zaak_update(self, data: Notification) -> None:
        zaak = retrieve_zaak(data["hoofd_object"])
        invalidate_zaak_cache(zaak)
        update_zaak_document(zaak)
        soft_update_related_zaak_in_objects(zaak)
        soft_update_related_zaak_in_docs(zaak)

    def _on_zaak_create(self, data: Notification) -> None:
        zaak_url = data["hoofd_object"]
        client = client_from_url(zaak_url)
        zaak = retrieve_zaak(zaak_url)

        invalidate_zaak_list_cache(client, zaak)

        zaak_doc = create_zaak_document(zaak)
        zaak_doc.zaaktype = create_zaaktype_document(zaak.zaaktype)
        if zaak.status:
            zaak_doc.status = create_status_document(zaak.status)
        zaak_doc.save(refresh=True)

    def _on_zaak_destroy(self, data: Notification) -> None:
        zaak_url = data["hoofd_object"]
        Activity.objects.filter(zaak=zaak_url).delete()
        BoardItem.objects.filter(object=zaak_url).delete()
        AccessRequest.objects.filter(zaak=zaak_url).delete()
        delete_zaak_document(zaak_url)

    # ---- Resultaat ----
    def _on_resultaat_create(self, data: Notification) -> None:
        zaak = retrieve_zaak(data["hoofd_object"])
        invalidate_zaak_cache(zaak)
        update_zaak_document(zaak)

    # ---- Status ----
    def _on_status_create(self, data: Notification) -> None:
        zaak = retrieve_zaak(data["hoofd_object"])
        invalidate_zaak_cache(zaak)

        zrc_client = client_from_url(data["resource_url"])
        status_dict = zrc_client.retrieve("status", url=data["resource_url"])
        status = factory(Status, status_dict)
        status.statustype = get_statustype(status.statustype)
        zaak.status = status

        if zaak.status.statustype.is_eindstatus:
            update_status_in_zaak_document(zaak)
            bulk_lock_review_requests_for_zaak(
                zaak, reason=f"Zaak is {zaak.status.statustype.omschrijving.lower()}."
            )
            bulk_close_all_documents_for_zaak(zaak)

            activities = Activity.objects.prefetch_related("events").filter(
                zaak=zaak.url, status=ActivityStatuses.on_going
            )
            for a in activities:
                a.user_assignee = None
                a.group_assignee = None
                a.status = ActivityStatuses.finished
                a.save()

            lock_checklist_for_zaak(zaak)

            task_name = settings.CAMUNDA_OPEN_BIJDRAGE_TASK_NAME + zaak.identificatie
            tasks = get_camunda_user_tasks(payload={"name": task_name}) or []
            for t in tasks:
                complete_task(t.id, variables={})
        else:
            update_status_in_zaak_document(zaak)

        update_zaak_document(zaak)

    # ---- Rol ----
    def _on_rol_create(self, data: Notification) -> None:
        zaak = retrieve_zaak(data["hoofd_object"])
        rol_url = data["resource_url"]

        invalidate_rollen_cache(zaak, rol_urls=[rol_url])
        updated = update_medewerker_identificatie_rol(rol_url, zaak=zaak)
        rol = fetch_rol(rol_url=rol_url)

        if not updated and (
            rol.omschrijving_generiek
            in {RolOmschrijving.behandelaar, RolOmschrijving.initiator}
        ):
            add_permission_for_behandelaar(rol_url)

        update_rollen_in_zaak_document(zaak)

    def _on_rol_destroy(self, data: Notification) -> None:
        zaak = retrieve_zaak(data["hoofd_object"])
        invalidate_rollen_cache(zaak)
        update_rollen_in_zaak_document(zaak)

    # ---- Zaakeigenschap ----
    def _on_zaakeigenschap_change(self, data: Notification) -> None:
        zaak = retrieve_zaak(data["hoofd_object"])
        invalidate_zaak_cache(zaak)
        invalidate_zaakeigenschappen_cache(zaak)
        update_eigenschappen_in_zaak_document(zaak)

    # ---- Zaakobject ----
    def _on_zaakobject_create(self, data: Notification) -> None:
        zaak = retrieve_zaak(data["hoofd_object"])
        invalidate_zaakobjecten_cache(zaak)

        zobj = fetch_zaakobject(data["resource_url"])
        doc = create_zaakobject_document(zobj)
        doc.save()
        update_related_zaken_in_object_document(zobj.object)

    def _on_zaakobject_destroy(self, data: Notification) -> None:
        zaak = retrieve_zaak(data["hoofd_object"])
        invalidate_zaakobjecten_cache(zaak)

        doc = get_zaakobject_document(data["resource_url"])
        if doc:
            update_related_zaken_in_object_document(doc.object)
            doc.delete()

    # ---- Zaakinformatieobject ----
    def _on_zaakinformatieobject_create(self, data: Notification) -> None:
        zio = fetch_zaak_informatieobject(data["resource_url"])
        doc = create_zaakinformatieobject_document(zio)
        doc.save()
        update_related_zaken_in_informatieobject_document(zio.informatieobject)

    def _on_zaakinformatieobject_update(self, data: Notification) -> None:
        zio = fetch_zaak_informatieobject(data["resource_url"])
        update_zaakinformatieobject_document(zio)
        update_related_zaken_in_informatieobject_document(zio.informatieobject)

    def _on_zaakinformatieobject_destroy(self, data: Notification) -> None:
        doc = get_zaakinformatieobject_document(data["resource_url"])
        if doc:
            update_related_zaken_in_informatieobject_document(doc.informatieobject)
            doc.delete()
