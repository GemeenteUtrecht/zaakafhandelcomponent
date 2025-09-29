import logging
from typing import Dict

from django.conf import settings

from django_camunda.api import complete_task, send_message
from elasticsearch.exceptions import NotFoundError
from requests.exceptions import HTTPError
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.constants import RolOmschrijving
from zgw_consumers.api_models.zaken import Status

from zac.accounts.models import AccessRequest
from zac.accounts.permission_loaders import add_permission_for_behandelaar
from zac.activities.constants import ActivityStatuses
from zac.activities.models import Activity
from zac.camunda.user_tasks.api import (
    get_camunda_user_tasks,
    get_camunda_user_tasks_for_zaak,
)
from zac.contrib.board.models import BoardItem
from zac.contrib.dowc.api import bulk_close_all_documents_for_zaak
from zac.contrib.objects.kownsl.cache import invalidate_review_requests_cache
from zac.contrib.objects.kownsl.data import ReviewRequest
from zac.contrib.objects.services import (
    bulk_lock_review_requests_for_zaak,
    lock_checklist_for_zaak,
)
from zac.core.cache import (
    invalidate_document_other_cache,
    invalidate_document_url_cache,
    invalidate_fetch_object_cache,
    invalidate_informatieobjecttypen_cache,
    invalidate_rollen_cache,
    invalidate_zaak_cache,
    invalidate_zaak_list_cache,
    invalidate_zaakeigenschappen_cache,
    invalidate_zaakobjecten_cache,
    invalidate_zaaktypen_cache,
)
from zac.core.models import MetaObjectTypesConfig
from zac.core.services import (
    client_from_url,
    delete_zaakobjecten_of_object,
    fetch_object,
    fetch_rol,
    fetch_zaak_informatieobject,
    fetch_zaakobject,
    fetch_zaaktype,
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
    delete_informatieobject_document,
    delete_object_document,
    delete_zaak_document,
    get_zaakinformatieobject_document,
    get_zaakobject_document,
    update_eigenschappen_in_zaak_document,
    update_informatieobject_document,
    update_object_document,
    update_related_zaak_in_informatieobject_documents,
    update_related_zaak_in_object_documents,
    update_related_zaken_in_informatieobject_document,
    update_related_zaken_in_object_document,
    update_rollen_in_zaak_document,
    update_status_in_zaak_document,
    update_zaak_document,
    update_zaakinformatieobject_document,
)
from zgw.models.zrc import Zaak

logger = logging.getLogger(__name__)


class ZakenHandler:
    def handle(self, data: dict) -> None:
        logger.debug("ZAC notification: %r" % data)
        if data["resource"] == "zaak":
            if data["actie"] == "create":
                self._handle_zaak_create(data["hoofd_object"])
            elif data["actie"] in ["update", "partial_update"]:
                self._handle_zaak_update(data["hoofd_object"])
            elif data["actie"] == "destroy":
                self._handle_zaak_destroy(data["hoofd_object"])

        elif data["resource"] == "zaakeigenschap":
            self._handle_zaakeigenschap_change(data["hoofd_object"])

        elif data["resource"] == "status" and data["actie"] == "create":
            self._handle_status_create(data)

        elif data["resource"] == "resultaat" and data["actie"] == "create":
            self._handle_related_create(data["hoofd_object"])

        elif data["resource"] == "rol":
            if data["actie"] == "create":
                self._handle_rol_create(
                    data["hoofd_object"], rol_url=data["resource_url"]
                )
            elif data["actie"] == "destroy":
                self._handle_rol_destroy(data["hoofd_object"])

        elif data["resource"] == "zaakobject":
            if data["actie"] == "create":
                self._handle_zaakobject_create(
                    data["hoofd_object"], data["resource_url"]
                )
            elif data["actie"] == "destroy":
                self._handle_zaakobject_destroy(
                    data["hoofd_object"], data["resource_url"]
                )

        elif data["resource"] == "zaakinformatieobject":
            if data["actie"] == "create":
                self._handle_zaakinformatieobject_create(
                    data["hoofd_object"], data["resource_url"]
                )
            elif data["actie"] == "update":
                self._handle_zaakinformatieobject_update(
                    data["hoofd_object"], data["resource_url"]
                )
            elif data["actie"] == "destroy":
                self._handle_zaakinformatieobject_destroy(
                    data["hoofd_object"], data["resource_url"]
                )

    @staticmethod
    def _retrieve_zaak(zaak_url) -> Zaak:
        zrc_client = client_from_url(zaak_url)
        zaak = zrc_client.retrieve(
            "zaak",
            url=zaak_url,
            request_kwargs={"headers": {"Accept-Crs": "EPSG:4326"}},
        )
        zaak = factory(Zaak, zaak)

        if isinstance(zaak.zaaktype, str):
            zaak.zaaktype = fetch_zaaktype(zaak.zaaktype)

        if zaak.status and isinstance(zaak.status, str):
            status = zrc_client.retrieve("status", url=zaak.status)
            status = factory(Status, status)
            status.statustype = get_statustype(status.statustype)
            zaak.status = status

        return zaak

    def _handle_zaak_update(self, zaak_url: str):
        # Invalidate cache
        zaak = self._retrieve_zaak(zaak_url)
        invalidate_zaak_cache(zaak)

        # index in ES
        update_zaak_document(zaak)

        # Update related zaak in objecten indices
        try:
            update_related_zaak_in_object_documents(zaak)
        except NotFoundError as exc:
            logger.warning("Could not find objecten index.")

        # Update related zaak in informatieobjecten indices
        try:
            update_related_zaak_in_informatieobject_documents(zaak)
        except NotFoundError as exc:
            logger.warning("Could not find informatieobjecten index.")

    def _handle_zaak_create(self, zaak_url: str):
        client = client_from_url(zaak_url)
        zaak = self._retrieve_zaak(zaak_url)
        invalidate_zaak_list_cache(client, zaak)
        # index in ES
        zaak_document = create_zaak_document(zaak)
        zaak_document.zaaktype = create_zaaktype_document(zaak.zaaktype)
        if zaak.status:
            zaak_document.status = create_status_document(zaak.status)

        zaak_document.save(refresh=True)

    def _handle_zaak_destroy(self, zaak_url: str):
        Activity.objects.filter(zaak=zaak_url).delete()
        BoardItem.objects.filter(object=zaak_url).delete()
        AccessRequest.objects.filter(zaak=zaak_url).delete()

        # update index in ES
        delete_zaak_document(zaak_url)

    def _handle_resultaat_create(self, zaak_url: str):
        zaak = self._retrieve_zaak(zaak_url)
        invalidate_zaak_cache(zaak)
        # update index in ES
        update_zaak_document(zaak)

    def _handle_status_create(self, data: Dict):
        zaak = self._retrieve_zaak(data["hoofd_object"])
        invalidate_zaak_cache(zaak)

        zrc_client = client_from_url(
            data["resource_url"]
        )  # make sure we fetch the status that was created HERE (could be race conditions)
        status = zrc_client.retrieve("status", url=data["resource_url"])
        status = factory(Status, status)
        status.statustype = get_statustype(status.statustype)
        zaak.status = status

        # if THIS status is set it means the zaak is closed ->
        if zaak.status.statustype.is_eindstatus:
            # Lock all review requests related to zaak
            bulk_lock_review_requests_for_zaak(
                zaak, reason=f"Zaak is {zaak.status.statustype.omschrijving.lower()}."
            )

            # Close all open documents
            bulk_close_all_documents_for_zaak(zaak)

            # Close all open activities
            activities = Activity.objects.prefetch_related("events").filter(
                zaak=zaak.url, status=ActivityStatuses.on_going
            )
            for activity in activities:
                activity.user_assignee = None
                activity.group_assignee = None
                activity.status = ActivityStatuses.finished
                activity.save()

            # Lock checklist
            lock_checklist_for_zaak(zaak)

            # Remove bijdragezaak tasks if they exist
            tasks = (
                get_camunda_user_tasks(
                    payload={
                        "name": settings.CAMUNDA_OPEN_BIJDRAGE_TASK_NAME
                        + zaak.identificatie
                    }
                )
                or []
            )
            for task in tasks:
                complete_task(task.id, variables=dict())

        # index in ES
        update_status_in_zaak_document(zaak)

    def _handle_rol_create(self, zaak_url: str, rol_url: str):
        zaak = self._retrieve_zaak(zaak_url)
        invalidate_rollen_cache(zaak, rol_urls=[rol_url])
        updated = update_medewerker_identificatie_rol(rol_url, zaak=zaak)

        rol = fetch_rol(rol_url=rol_url)
        if not updated and (
            rol.omschrijving_generiek
            in [RolOmschrijving.behandelaar, RolOmschrijving.initiator]
        ):
            add_permission_for_behandelaar(rol_url)

        update_rollen_in_zaak_document(zaak)

    def _handle_rol_destroy(self, zaak_url: str):
        zaak = self._retrieve_zaak(zaak_url)
        invalidate_rollen_cache(zaak)

        # index in ES
        update_rollen_in_zaak_document(zaak)

    def _handle_zaakeigenschap_change(self, zaak_url: str):
        zaak = self._retrieve_zaak(zaak_url)
        invalidate_zaak_cache(zaak)
        invalidate_zaakeigenschappen_cache(zaak)

        # index in ES
        update_eigenschappen_in_zaak_document(zaak)

    def _handle_zaakobject_create(self, zaak_url: str, zaakobject_url: str):
        # Invalidate zaakobjecten cache with zaak
        zaak = self._retrieve_zaak(zaak_url)
        invalidate_zaakobjecten_cache(zaak)

        zaakobject = fetch_zaakobject(zaakobject_url)
        # index in zaakobjecten
        zod = create_zaakobject_document(zaakobject)
        zod.save()

        # index in objecten
        update_related_zaken_in_object_document(zaakobject.object)

    def _handle_zaakobject_destroy(self, zaak_url: str, zaakobject_url: str):
        # Invalidate zaakobjecten cache with zaak
        zaak = self._retrieve_zaak(zaak_url)
        invalidate_zaakobjecten_cache(zaak)

        # Get zaakobjectdocument
        zaakobjectdocument = get_zaakobject_document(zaakobject_url)

        if zaakobjectdocument:  # update related_zaken in objecten index
            update_related_zaken_in_object_document(zaakobjectdocument.object)
            # delete from zaakobject index
            zaakobjectdocument.delete()

    def _handle_zaakinformatieobject_create(
        self, zaak_url: str, zaakinformatieobject_url: str
    ):
        zaakinformatieobject = fetch_zaak_informatieobject(zaakinformatieobject_url)

        # Index in zaakinformatieobject index
        ziod = create_zaakinformatieobject_document(zaakinformatieobject)
        ziod.save()

        # update related_zaken in informatieobjecten index
        update_related_zaken_in_informatieobject_document(
            zaakinformatieobject.informatieobject
        )

    def _handle_zaakinformatieobject_update(
        self, zaak_url: str, zaakinformatieobject_url: str
    ):
        zaakinformatieobject = fetch_zaak_informatieobject(zaakinformatieobject_url)

        # update zaakinformatieobject index
        update_zaakinformatieobject_document(zaakinformatieobject)

        # update related_zaken in informatieobjecten index
        update_related_zaken_in_informatieobject_document(
            zaakinformatieobject.informatieobject
        )

    def _handle_zaakinformatieobject_destroy(
        self, zaak_url: str, zaakinformatieobject_url: str
    ):

        # Get zaakinformatieobject document
        ziod = get_zaakinformatieobject_document(zaakinformatieobject_url)

        # update related_zaken in informatieobjecten index
        update_related_zaken_in_informatieobject_document(ziod.informatieobject)

        # delete from zaakinformatieobject index
        ziod.delete()


class ZaaktypenHandler:
    def handle(self, data: dict) -> None:
        if data["resource"] == "zaaktype":
            if data["actie"] in ["create", "update", "partial_update"]:
                invalidate_zaaktypen_cache(catalogus=data["kenmerken"]["catalogus"])
                invalidate_zaaktypen_cache()


class InformatieObjecttypenHandler:
    def handle(self, data: dict) -> None:
        if data["resource"] == "informatieobjecttype":
            if data["actie"] in ["create", "update", "partial_update"]:
                invalidate_informatieobjecttypen_cache(
                    catalogus=data["kenmerken"]["catalogus"]
                )
                invalidate_informatieobjecttypen_cache()


class ObjectenHandler:
    def _review_request_object_handler(self, data: dict) -> None:
        rr = factory(ReviewRequest, data["record"]["data"])
        invalidate_review_requests_cache(rr)
        if rr.locked:
            # End the current process instance gracefully
            try:
                send_message(
                    "cancel-process",
                    [rr.metadata.get("process_instance_id")],
                )
            except HTTPError as exc:
                logger.info(
                    "Something went wrong trying to end process instance gracefully. Process instance might not exist anymore.",
                    exc_info=True,
                )

    def _meta_object_handler(self) -> Dict[str, callable]:
        meta_config = MetaObjectTypesConfig.get_solo()
        return {
            meta_config.review_request_objecttype: self._review_request_object_handler
        }

    # We dont update related_zaken here - the notification from open zaak takes care of that.
    def handle(self, data: dict) -> None:
        if data["resource"] == "object":
            invalidate_fetch_object_cache(data["hoofd_object"])
            if data["actie"] in ["create", "update", "partial_update"]:
                object = fetch_object(data["hoofd_object"])
                meta_object_handler = self._meta_object_handler()
                if func := meta_object_handler.get(object["type"]["url"], None):
                    func(object)

                # Don't index meta objects.
                if (
                    object["type"]["url"]
                    not in MetaObjectTypesConfig.get_solo().meta_objecttype_urls.values()
                ):
                    update_object_document(object)

            elif data["actie"] == "destroy":
                delete_object_document(data["hoofd_object"])
                delete_zaakobjecten_of_object(data["hoofd_object"])


class InformatieObjectenHandler:
    # We dont update related_zaken here - the notification from open zaak takes care of that.
    def handle(self, data: dict) -> None:
        if data["resource"] == "enkelvoudiginformatieobject":
            if (actie := data["actie"]) in ["create", "update", "partial_update"]:
                invalidate_document_url_cache(data["hoofd_object"])
                document = get_document(data["hoofd_object"])
                invalidate_document_other_cache(document)
                update_informatieobject_document(document)

                # in edge cases a destroyed EIO can be restored.
                # in this case check at creation for existing zaakinformatieobjecten in ES
                if actie == "create":
                    update_related_zaken_in_informatieobject_document(document.url)

            elif data["actie"] == "destroy":
                invalidate_document_url_cache(data["hoofd_object"])
                delete_informatieobject_document(data["hoofd_object"])


class RoutingHandler:
    def __init__(self, config: dict, default=None):
        self.config = config
        self.default = default

    def handle(self, message: dict) -> None:
        handler = self.config.get(message["kanaal"])
        if handler is not None:
            handler.handle(message)
        elif self.default:
            self.default.handle(message)


handler = RoutingHandler(
    {
        "zaaktypen": ZaaktypenHandler(),
        "informatieobjecttypen": InformatieObjecttypenHandler(),
        "zaken": ZakenHandler(),
        "objecten": ObjectenHandler(),
        "documenten": InformatieObjectenHandler(),
    }
)
