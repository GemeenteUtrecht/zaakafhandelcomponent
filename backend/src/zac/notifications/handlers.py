from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.api_models.zaken import Status

from zac.accounts.permission_loaders import add_permission_for_behandelaar
from zac.activities.models import Activity
from zac.contrib.board.models import BoardItem
from zac.core.cache import (
    invalidate_informatieobjecttypen_cache,
    invalidate_rollen_cache,
    invalidate_zaak_cache,
    invalidate_zaak_list_cache,
    invalidate_zaakobjecten_cache,
    invalidate_zaaktypen_cache,
)
from zac.core.services import (
    _client_from_url,
    get_rollen,
    update_medewerker_identificatie_rol,
)
from zac.elasticsearch.api import (
    create_status_document,
    create_zaak_document,
    create_zaaktype_document,
    delete_zaak_document,
    update_eigenschappen_in_zaak_document,
    update_rollen_in_zaak_document,
    update_status_in_zaak_document,
    update_zaak_document,
    update_zaakobjecten_in_zaak_document,
)
from zgw.models.zrc import Zaak


class ZakenHandler:
    def handle(self, data: dict) -> None:
        if data["resource"] == "zaak":
            if data["actie"] == "create":
                self._handle_zaak_creation(data["hoofd_object"])
            elif data["actie"] in ["update", "partial_update"]:
                self._handle_zaak_update(data["hoofd_object"])
            elif data["actie"] == "destroy":
                self._handle_zaak_destroy(data["hoofd_object"])

        elif data["resource"] == "zaakeigenschap":
            self._handle_zaakeigenschap_change(data["hoofd_object"])

        elif data["resource"] == "status" and data["actie"] == "create":
            self._handle_status_creation(data["hoofd_object"])

        elif data["resource"] == "resultaat" and data["actie"] == "create":
            self._handle_related_creation(data["hoofd_object"])

        elif data["resource"] == "rol":
            self._handle_rol_change(data["hoofd_object"])
            # TODO should we remove permission if the rol is deleted?
            if data["actie"] == "create":
                add_permission_for_behandelaar(rol=data["resource_url"])

        elif data["resource"] == "zaakobject":
            self._handle_zaakobject_change(data["hoofd_object"])

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

        # index in ES
        update_zaak_document(zaak)

    def _handle_zaak_creation(self, zaak_url: str):
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
        # index in ES
        delete_zaak_document(zaak_url)

    def _handle_related_creation(self, zaak_url: str):
        zaak = self._retrieve_zaak(zaak_url)
        invalidate_zaak_cache(zaak)

    def _handle_status_creation(self, zaak_url: str):
        zaak = self._retrieve_zaak(zaak_url)
        invalidate_zaak_cache(zaak)

        # index in ES
        update_status_in_zaak_document(zaak)

    def _handle_rol_change(self, zaak_url: str):
        zaak = self._retrieve_zaak(zaak_url)

        # Invalidate cache for get_rollen in update_medewerker_identificatie_rol
        rollen = get_rollen(zaak)
        invalidate_rollen_cache(zaak, rollen=rollen)

        # See if medewerker rollen have all the necessary fields
        updated_rollen = update_medewerker_identificatie_rol(zaak)
        if (
            updated_rollen
        ):  # Invalidate cache for get_rollen in update_rollen_in_zaak_document
            invalidate_rollen_cache(zaak)

        # index in ES
        update_rollen_in_zaak_document(zaak)

    def _handle_zaakeigenschap_change(self, zaak_url: str):
        zaak = self._retrieve_zaak(zaak_url)
        invalidate_zaak_cache(zaak)

        # index in ES
        update_eigenschappen_in_zaak_document(zaak)

    def _handle_zaakobject_change(self, zaak_url: str):
        zaak = self._retrieve_zaak(zaak_url)
        invalidate_zaakobjecten_cache(zaak)

        # index in ES
        update_zaakobjecten_in_zaak_document(zaak)


class ZaaktypenHandler:
    def handle(self, data: dict) -> None:
        if data["resource"] == "zaaktype":
            if data["actie"] in ["create", "update", "partial_update"]:
                invalidate_zaaktypen_cache(catalogus=data["kenmerken"]["catalogus"])


class InformatieObjecttypenHandler:
    def handle(self, data: dict) -> None:
        if data["resource"] == "informatieobjecttype":
            if data["actie"] in ["create", "update", "partial_update"]:
                invalidate_informatieobjecttypen_cache(
                    catalogus=data["kenmerken"]["catalogus"]
                )


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
    }
)
