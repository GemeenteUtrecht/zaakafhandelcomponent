import logging
from collections import defaultdict
from typing import Optional

from elasticsearch import exceptions
from zgw_consumers.api_models.catalogi import StatusType, ZaakType
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.api_models.zaken import Status

from zac.core.rollen import Rol
from zac.core.services import (
    fetch_zaaktype,
    get_rollen,
    get_status,
    get_statustype,
    get_zaak_eigenschappen,
    get_zaakobjecten,
)
from zgw.models.zrc import Zaak

from .documents import (
    RolDocument,
    StatusDocument,
    ZaakDocument,
    ZaakObjectDocument,
    ZaakTypeDocument,
)

logger = logging.getLogger(__name__)


def _get_uuid_from_url(url: str):
    return url.strip("/").split("/")[-1]


def create_zaak_document(zaak: Zaak) -> ZaakDocument:
    zaak.zaaktype = (
        zaak.zaaktype
        if isinstance(zaak.zaaktype, ZaakType)
        else fetch_zaaktype(zaak.zaaktype)
    )
    zaaktype_document = ZaakTypeDocument(
        url=zaak.zaaktype.url,
        omschrijving=zaak.zaaktype.omschrijving,
        catalogus=zaak.zaaktype.catalogus,
    )
    if zaak.status:
        status_document = _create_status_document(zaak)
    else:
        status_document = None

    zaakobjecten = [
        ZaakObjectDocument(
            url=zo.url,
            object=zo.object,
        )
        for zo in get_zaakobjecten(zaak)
    ]

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
        deadline=zaak.deadline,
        status=status_document,
        toelichting=zaak.toelichting,
        zaakobjecten=zaakobjecten,
    )
    zaak_document.save()
    # TODO check rollen in case of update
    return zaak_document


def _get_zaak_document(
    zaak_uuid: str, zaak_url: str, create_zaak: Optional[Zaak] = None
) -> Optional[ZaakDocument]:
    try:
        zaak_document = ZaakDocument.get(id=zaak_uuid)
    except exceptions.NotFoundError as exc:
        logger.warning("zaak %s hasn't been indexed in ES", zaak_url, exc_info=True)
        if not create_zaak:
            return
        else:
            zaak_document = create_zaak_document(create_zaak)
    return zaak_document


def update_zaak_document(zaak: Zaak) -> ZaakDocument:
    zaak_document = _get_zaak_document(zaak.uuid, zaak.url, create_zaak=zaak)

    # Don't include zaaktype and identificatie since they are immutable.
    # Don't include status or objecten as those are handled through a
    # different handler in the notifications api.
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
        deadline=zaak.deadline,
        toelichting=zaak.toelichting,
    )
    return zaak_document


def delete_zaak_document(zaak_url: str) -> None:
    zaak_uuid = _get_uuid_from_url(zaak_url)
    zaak_document = _get_zaak_document(zaak_uuid, zaak_url)
    if zaak_document:
        zaak_document.delete()

    return


def append_rol_to_document(rol: Rol) -> None:
    rol_document = RolDocument(
        url=rol.url,
        betrokkene_type=rol.betrokkene_type,
        betrokkene_identificatie=rol.betrokkene_identificatie,
        omschrijving_generiek=rol.omschrijving_generiek,
    )

    # add rol document to zaak
    zaak_uuid = rol.zaak.strip("/").split("/")[-1]
    zaak_document = _get_zaak_document(zaak_uuid, rol.zaak)
    if zaak_document:
        zaak_document.rollen.append(rol_document)
        zaak_document.save()

    return


def update_rollen_in_zaak_document(zaak: Zaak) -> None:
    zaak_document = _get_zaak_document(zaak.uuid, zaak.url, create_zaak=zaak)
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

    return


def update_eigenschappen_in_zaak_document(zaak: Zaak) -> None:
    zaak_document = _get_zaak_document(zaak.uuid, zaak.url, create_zaak=zaak)

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

    return


def update_zaakobjecten_in_zaak_document(zaak: Zaak) -> None:
    zaak_document = _get_zaak_document(zaak.uuid, zaak.url, create_zaak=zaak)
    zaak_document.objecten = [
        ZaakObjectDocument(
            url=zo.url,
            object=zo.object,
        )
        for zo in get_zaakobjecten(zaak)
    ]
    zaak_document.save()

    return


def _create_status_document(zaak: Zaak) -> StatusDocument:
    status = zaak.status if isinstance(zaak.status, Status) else get_status(zaak)
    status.statustype = (
        status.statustype
        if isinstance(status.statustype, StatusType)
        else get_statustype(status.statustype)
    )
    status_document = StatusDocument(
        url=status.url,
        statustype=status.statustype.omschrijving,
        datum_status_gezet=status.datum_status_gezet,
        statustoelichting=status.statustoelichting,
    )
    return status_document


def update_status_in_zaak_document(zaak: Zaak) -> None:
    zaak_document = _get_zaak_document(zaak.uuid, zaak.url, create_zaak=zaak)
    status_document = _create_status_document(zaak)
    zaak_document.status = status_document
    zaak_document.save()

    return
