import logging

from elasticsearch import exceptions
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen

from zac.core.rollen import Rol
from zac.core.services import get_rollen
from zgw.models.zrc import Zaak

from .documents import RolDocument, ZaakDocument

logger = logging.getLogger(__name__)


def _get_uuid_from_url(url: str):
    return url.strip("/").split("/")[-1]


def create_zaak_document(zaak: Zaak) -> ZaakDocument:
    zaaktype_url = (
        zaak.zaaktype if isinstance(zaak.zaaktype, str) else zaak.zaaktype.url
    )

    zaak_document = ZaakDocument(
        meta={"id": zaak.uuid},
        url=zaak.url,
        zaaktype=zaaktype_url,
        identificatie=zaak.identificatie,
        bronorganisatie=zaak.bronorganisatie,
        vertrouwelijkheidaanduiding=zaak.vertrouwelijkheidaanduiding,
        va_order=VertrouwelijkheidsAanduidingen.get_choice(
            zaak.vertrouwelijkheidaanduiding
        ).order,
        startdatum=zaak.startdatum,
        einddatum=zaak.einddatum,
        registratiedatum=zaak.registratiedatum,
    )
    zaak_document.save()
    # TODO check rollen in case of update
    return zaak_document


def update_zaak_document(zaak: Zaak) -> ZaakDocument:
    try:
        zaak_document = ZaakDocument.get(id=zaak.uuid)
    except exceptions.NotFoundError as exc:
        logger.warning("zaak %s hasn't been indexed in ES", zaak.url, exc_info=True)
        return create_zaak_document(zaak)

    zaaktype_url = (
        zaak.zaaktype if isinstance(zaak.zaaktype, str) else zaak.zaaktype.url
    )
    zaak_document.update(
        refresh=True,
        zaaktype=zaaktype_url,
        identificatie=zaak.identificatie,
        bronorganisatie=zaak.bronorganisatie,
        vertrouwelijkheidaanduiding=zaak.vertrouwelijkheidaanduiding,
        va_order=VertrouwelijkheidsAanduidingen.get_choice(
            zaak.vertrouwelijkheidaanduiding
        ).order,
        startdatum=zaak.startdatum,
        einddatum=zaak.einddatum,
        registratiedatum=zaak.registratiedatum,
    )
    return zaak_document


def delete_zaak_document(zaak_url: str) -> None:
    zaak_uuid = _get_uuid_from_url(zaak_url)
    try:
        zaak_document = ZaakDocument.get(id=zaak_uuid)
    except exceptions.NotFoundError as exc:
        logger.warning("zaak %s hasn't been indexed in ES", zaak_url, exc_info=True)
        return
    zaak_document.delete()


def append_rol_to_document(rol: Rol):
    rol_document = RolDocument(
        url=rol.url,
        betrokkene_type=rol.betrokkene_type,
        betrokkene_identificatie=rol.betrokkene_identificatie,
        omschrijving_generiek=rol.omschrijving_generiek,
    )

    # add rol document to zaak
    zaak_uuid = rol.zaak.strip("/").split("/")[-1]
    try:
        zaak_document = ZaakDocument.get(id=zaak_uuid)
    except exceptions.NotFoundError as exc:
        logger.warning("zaak %s hasn't been indexed in ES", rol.zaak, exc_info=True)
        return

    zaak_document.rollen.append(rol_document)
    zaak_document.save()


def update_rollen_in_zaak_document(zaak: Zaak):
    try:
        zaak_document = ZaakDocument.get(id=zaak.uuid)
    except exceptions.NotFoundError as exc:
        logger.warning("zaak %s hasn't been indexed in ES", zaak.url, exc_info=True)
        zaak_document = create_zaak_document(zaak)

    rol_documents = [
        RolDocument(
            url=rol.url,
            betrokkene_type=rol.betrokkene_type,
            betrokkene_identificatie=rol.betrokkene_identificatie,
            omschrijving_generiek=rol.omschrijving_generiek,
        )
        for rol in get_rollen(zaak)
    ]

    zaak_document.rollen = rol_documents
    zaak_document.save()
