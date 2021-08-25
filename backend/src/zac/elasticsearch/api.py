import logging
from collections import defaultdict
from typing import List, Optional

from elasticsearch import exceptions
from zgw_consumers.api_models.catalogi import StatusType, ZaakType
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.api_models.zaken import Status, ZaakEigenschap, ZaakObject

from zac.core.rollen import Rol
from zac.core.services import (
    get_rollen,
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
    zaak_document = ZaakDocument(
        meta={"id": zaak.uuid},
        url=zaak.url,
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
        toelichting=zaak.toelichting,
    )

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


def get_zaak_document(zaak_url: str):
    zaak_uuid = _get_uuid_from_url(zaak_url)
    return _get_zaak_document(zaak_uuid, zaak_url)


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


def create_zaaktype_document(zaaktype: ZaakType) -> ZaakTypeDocument:
    zaaktype_document = ZaakTypeDocument(
        url=zaaktype.url,
        omschrijving=zaaktype.omschrijving,
        catalogus=zaaktype.catalogus,
    )

    return zaaktype_document


def create_status_document(status: Status) -> StatusDocument:
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
    status_document = create_status_document(zaak.status) if zaak.status else None

    zaak_document = _get_zaak_document(zaak.uuid, zaak.url, create_zaak=zaak)
    zaak_document.status = status_document
    zaak_document.save()

    return


def create_rol_document(rol: Rol) -> RolDocument:
    rol_document = RolDocument(
        url=rol.url,
        betrokkene_type=rol.betrokkene_type,
        betrokkene_identificatie=rol.betrokkene_identificatie,
        omschrijving_generiek=rol.omschrijving_generiek,
    )

    return rol_document


def update_rollen_in_zaak_document(zaak: Zaak) -> None:
    rol_documents = [create_rol_document(rol) for rol in get_rollen(zaak)]

    zaak_document = _get_zaak_document(zaak.uuid, zaak.url, create_zaak=zaak)
    zaak_document.rollen = rol_documents
    zaak_document.save()

    return


def create_eigenschappen_document(eigenschappen: List[ZaakEigenschap]) -> dict:
    eigenschappen_doc = defaultdict(dict)
    for zaak_eigenschap in eigenschappen:
        spec_format = zaak_eigenschap.eigenschap.specificatie.formaat
        # replace points in the field name because ES can't process them
        # see https://discuss.elastic.co/t/class-cast-exception-for-dynamic-field-with-in-its-name/158819/5
        eigenschappen_doc[spec_format].update(
            {zaak_eigenschap.naam.replace(".", " "): zaak_eigenschap.waarde}
        )

    return eigenschappen_doc


def update_eigenschappen_in_zaak_document(zaak: Zaak) -> None:
    zaak.eigenschappen = get_zaak_eigenschappen(zaak)
    eigenschappen_doc = create_eigenschappen_document(zaak.eigenschappen)

    zaak_document = _get_zaak_document(zaak.uuid, zaak.url, create_zaak=zaak)
    zaak_document.eigenschappen = eigenschappen_doc
    zaak_document.save()

    return


def create_zaakobject_document(
    zaakobject: ZaakObject,
) -> ZaakObjectDocument:
    return ZaakObjectDocument(url=zaakobject.url, object=zaakobject.object)


def update_zaakobjecten_in_zaak_document(zaak: Zaak) -> None:
    zaak.zaakobjecten = get_zaakobjecten(zaak)

    zaak_document = _get_zaak_document(zaak.uuid, zaak.url, create_zaak=zaak)
    zaak_document.zaakobjecten = [
        create_zaakobject_document(zo) for zo in zaak.zaakobjecten
    ]
    zaak_document.save()

    return
