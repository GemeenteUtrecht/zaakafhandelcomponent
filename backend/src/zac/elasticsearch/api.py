import logging
from collections import defaultdict

from elasticsearch import exceptions
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen

from zac.core.rollen import Rol
from zac.core.services import fetch_zaaktype, get_rollen, get_zaak_eigenschappen
from zgw.models.zrc import Zaak

from .documents import RolDocument, ZaakDocument, ZaakTypeDocument

logger = logging.getLogger(__name__)


def _get_uuid_from_url(url: str):
    return url.strip("/").split("/")[-1]


def create_zaak_document(zaak: Zaak) -> ZaakDocument:
    zaaktype = (
        zaak.zaaktype
        if isinstance(zaak.zaaktype, ZaakType)
        else fetch_zaaktype(zaak.zaaktype)
    )
    zaaktype_document = ZaakTypeDocument(
        url=zaaktype.url,
        omschrijving=zaaktype.omschrijving,
        catalogus=zaaktype.catalogus,
    )

    zaak_document = ZaakDocument(
        meta={"id": zaak.uuid},
        url=zaak.url,
        zaaktype=zaaktype_document,
        identificatie=zaak.identificatie,
        bronorganisatie=zaak.bronorganisatie,
        omschrijving=zaak.omschrijving,
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

    #  don't include zaaktype and identificatie since they are immutable
    zaak_document.update(
        refresh=True,
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


def update_eigenschappen_in_zaak_document(zaak: Zaak):
    try:
        zaak_document = ZaakDocument.get(id=zaak.uuid)
    except exceptions.NotFoundError as exc:
        logger.warning("zaak %s hasn't been indexed in ES", zaak.url, exc_info=True)
        zaak_document = create_zaak_document(zaak)

    eigenschappen_doc = defaultdict(dict)
    for zaak_eigenschap in get_zaak_eigenschappen(zaak):
        spec_format = zaak_eigenschap.eigenschap.specificatie.formaat
        # replace points in the field name because ES can't process them
        # see https://discuss.elastic.co/t/class-cast-exception-for-dynamic-field-with-in-its-name/158819/5
        eigenschappen_doc[spec_format].update(
            {zaak_eigenschap.naam.replace(".", " "): zaak_eigenschap.waarde}
        )

    zaak_document.eigenschappen = eigenschappen_doc
    zaak_document.save()
