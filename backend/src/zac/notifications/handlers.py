import logging

from elasticsearch.exceptions import NotFoundError
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.api_models.constants import RolOmschrijving
from zgw_consumers.api_models.zaken import Status
from zgw_consumers.concurrent import parallel

from zac.accounts.models import AccessRequest
from zac.accounts.permission_loaders import add_permission_for_behandelaar
from zac.activities.models import Activity
from zac.contrib.board.models import BoardItem
from zac.contrib.kownsl.api import get_review_requests, partial_update_review_request
from zac.contrib.kownsl.data import ReviewRequest
from zac.core.cache import (
    invalidate_document_cache,
    invalidate_document_url_cache,
    invalidate_fetch_object_cache,
    invalidate_informatieobjecttypen_cache,
    invalidate_rollen_cache,
    invalidate_zaak_cache,
    invalidate_zaak_list_cache,
    invalidate_zaakobjecten_cache,
    invalidate_zaaktypen_cache,
)
from zac.core.services import (
    _client_from_url,
    fetch_object,
    fetch_rol,
    fetch_zaak_informatieobject,
    fetch_zaak_object,
    get_document,
    update_medewerker_identificatie_rol,
)
from zac.elasticsearch.api import (
    create_status_document,
    create_zaak_document,
    create_zaaktype_document,
    delete_informatieobject_document,
    delete_object_document,
    delete_zaak_document,
    get_zaak_document,
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
    update_zaakinformatieobjecten_in_zaak_document,
    update_zaakobjecten_in_zaak_document,
)
from zac.elasticsearch.documents import ZaakDocument
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
            self._handle_status_create(data["hoofd_object"])

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
            elif data["actie"] == "destroy":
                self._handle_zaakinformatieobject_destroy(
                    data["hoofd_object"], data["resource_url"]
                )

    @staticmethod
    def _retrieve_zaak(zaak_url) -> Zaak:
        client = _client_from_url(zaak_url)
        zaak = client.retrieve("zaak", url=zaak_url)

        if isinstance(zaak["zaaktype"], str):
            zrc_client = _client_from_url(zaak["zaaktype"])
            zaaktype = zrc_client.retrieve("zaaktype", url=zaak["zaaktype"])
            zaak["zaaktype"] = factory(ZaakType, zaaktype)

        zaak = factory(Zaak, zaak)
        if zaak.status and isinstance(zaak.status, str):
            zrc_client = _client_from_url(zaak.status)
            status = zrc_client.retrieve("status", url=zaak.status)
            zaak.status = factory(Status, status)

        return zaak

    def _handle_zaak_update(self, zaak_url: str):
        # Invalidate cache
        zaak = self._retrieve_zaak(zaak_url)
        invalidate_zaak_cache(zaak)

        # Determine if einddatum is updated.
        if is_closed := zaak.einddatum:
            zaak_document = get_zaak_document(zaak_url)
            was_closed = None if not zaak_document else zaak_document.einddatum

            def _partial_update_review_request(rr: ReviewRequest):
                partial_update_review_request(
                    str(rr.id), data={"lock_reason": "Zaak is gesloten."}
                )

            # lock all review requests related to zaak
            if is_closed and is_closed != was_closed:
                review_requests = get_review_requests(zaak)
                with parallel() as executor:
                    list(executor.map(_partial_update_review_request, review_requests))

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
        client = _client_from_url(zaak_url)
        zaak = self._retrieve_zaak(zaak_url)
        invalidate_zaak_list_cache(client, zaak)
        # index in ES
        zaak_document = create_zaak_document(zaak)
        zaak_document.zaaktype = create_zaaktype_document(zaak.zaaktype)
        if zaak.status:
            zaak_document.status = create_status_document(zaak.status)

        zaak_document.save()

    def _handle_zaak_destroy(self, zaak_url: str):
        Activity.objects.filter(zaak=zaak_url).delete()
        BoardItem.objects.filter(object=zaak_url).delete()
        AccessRequest.objects.filter(zaak=zaak_url).delete()

        # index in ES
        delete_zaak_document(zaak_url)

    def _handle_related_create(self, zaak_url: str):
        zaak = self._retrieve_zaak(zaak_url)
        invalidate_zaak_cache(zaak)

    def _handle_status_create(self, zaak_url: str):
        zaak = self._retrieve_zaak(zaak_url)
        invalidate_zaak_cache(zaak)

        # index in ES
        update_status_in_zaak_document(zaak)

    def _handle_rol_create(self, zaak_url: str, rol_url: str):
        zaak = self._retrieve_zaak(zaak_url)
        invalidate_rollen_cache(zaak, rol_urls=[rol_url])
        updated = update_medewerker_identificatie_rol(rol_url)

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

        # index in ES
        update_eigenschappen_in_zaak_document(zaak)

    def _handle_zaakobject_create(self, zaak_url: str, zaakobject_url: str):
        # Invalidate zaakobjecten cache with zaak
        zaak = self._retrieve_zaak(zaak_url)
        invalidate_zaakobjecten_cache(zaak)

        # index in zaken
        update_zaakobjecten_in_zaak_document(zaak)

        # index in objecten
        zaakobject = fetch_zaak_object(zaakobject_url)
        update_related_zaken_in_object_document(zaakobject.object)

    def _handle_zaakobject_destroy(self, zaak_url: str, zaakobject_url: str):
        # Invalidate zaakobjecten cache with zaak
        zaak = self._retrieve_zaak(zaak_url)
        invalidate_zaakobjecten_cache(zaak)

        # Get zaakobject from ZaakDocument
        zaakdocument = ZaakDocument.get(id=zaak.uuid)
        object_url = None
        for zo in zaakdocument.zaakobjecten:
            if zo.url == zaakobject_url:
                object_url = zo.object

        # update zaken index
        update_zaakobjecten_in_zaak_document(zaak)

        # update related_zaken in objecten index
        update_related_zaken_in_object_document(object_url)

    def _handle_zaakinformatieobject_create(
        self, zaak_url: str, zaakinformatieobject_url: str
    ):
        zaak = self._retrieve_zaak(zaak_url)
        # No need to invalidate cache as zaakinformatieobjecten aren't cached?

        # update zaken index
        update_zaakinformatieobjecten_in_zaak_document(zaak)

        # update related_zaken in informatieobjecten index
        zaakinformatieobject = fetch_zaak_informatieobject(zaakinformatieobject_url)
        update_related_zaken_in_informatieobject_document(
            zaakinformatieobject.informatieobject
        )

    def _handle_zaakinformatieobject_destroy(
        self, zaak_url: str, zaakinformatieobject_url: str
    ):
        zaak = self._retrieve_zaak(zaak_url)
        # No need to invalidate cache as zaakinformatieobjecten aren't cached?

        # Get zaakobject from ZaakDocument
        zaakdocument = ZaakDocument.get(id=zaak.uuid)
        informatieobject_url = None
        for zio in zaakdocument.zaakinformatieobjecten:
            if zio.url == zaakinformatieobject_url:
                informatieobject_url = zio.informatieobject

        # update zaken index
        update_zaakinformatieobjecten_in_zaak_document(zaak)

        # update related_zaken in informatieobjecten index
        update_related_zaken_in_informatieobject_document(informatieobject_url)


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
    # We dont update related_zaken here - the notification from open zaak takes care of that.
    def handle(self, data: dict) -> None:
        if data["resource"] == "objecten":
            invalidate_fetch_object_cache(data["hoofd_object"])
            if data["actie"] in ["create", "update", "partial_update"]:
                object = fetch_object(data["hoofd_object"])
                update_object_document(object)

            elif data["actie"] == "destroy":
                delete_object_document(data["hoofd_object"])


class InformatieObjectenHandler:
    # We dont update related_zaken here - the notification from open zaak takes care of that.
    def handle(self, data: dict) -> None:
        if data["resource"] == "documenten":
            if data["actie"] in ["create", "update", "partial_update"]:
                document = get_document(data["hoofd_object"])
                invalidate_document_cache(document)
                document = get_document(data["hoofd_object"])
                update_informatieobject_document(document)

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
