import logging
from collections import defaultdict
from typing import Dict, List, Optional, Union

from elasticsearch import exceptions
from elasticsearch_dsl.query import Bool, Nested, Term
from zgw_consumers.api_models.catalogi import StatusType, ZaakType
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.api_models.zaken import Status, ZaakEigenschap, ZaakObject
from zgw_consumers.concurrent import parallel

from zac.accounts.datastructures import VA_ORDER
from zac.core.rollen import Rol
from zac.core.services import (
    fetch_object,
    fetch_zaaktype,
    get_document,
    get_rollen,
    get_status,
    get_statustype,
    get_zaak,
    get_zaak_eigenschappen,
    get_zaak_informatieobjecten,
    get_zaakinformatieobjecten_related_to_informatieobject,
    get_zaakobjecten,
    get_zaakobjecten_related_to_object,
    get_zaaktypen,
)
from zgw.models.zrc import Zaak, ZaakInformatieObject

from .documents import (
    InformatieObjectDocument,
    ObjectDocument,
    ObjectTypeDocument,
    RelatedZaakDocument,
    RolDocument,
    StatusDocument,
    ZaakDocument,
    ZaakObjectDocument,
    ZaakTypeDocument,
)

logger = logging.getLogger(__name__)


def _get_uuid_from_url(url: str) -> str:
    return url.strip("/").split("/")[-1]


###################################################
#                       ZRC                       #
###################################################


def create_zaak_document(zaak: Zaak) -> ZaakDocument:
    zaak_document = ZaakDocument(
        meta={"id": zaak.uuid},
        url=zaak.url,
        identificatie=zaak.identificatie,
        bronorganisatie=zaak.bronorganisatie,
        omschrijving=zaak.omschrijving,
        vertrouwelijkheidaanduiding=zaak.vertrouwelijkheidaanduiding,
        va_order=VA_ORDER[zaak.vertrouwelijkheidaanduiding],
        startdatum=zaak.startdatum,
        einddatum=zaak.einddatum,
        registratiedatum=zaak.registratiedatum,
        deadline=zaak.deadline,
        toelichting=zaak.toelichting,
        zaakgeometrie=zaak.zaakgeometrie,
        identificatie_suggest=zaak.identificatie,
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
            zaak_document.save()

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
        va_order=VA_ORDER[zaak.vertrouwelijkheidaanduiding],
        startdatum=zaak.startdatum,
        einddatum=zaak.einddatum,
        registratiedatum=zaak.registratiedatum,
        deadline=zaak.deadline,
        toelichting=zaak.toelichting,
        zaakgeometrie=zaak.zaakgeometrie,
        omschrijving=zaak.omschrijving,
        identificatie_suggest=zaak.identificatie,
    )
    return zaak_document


def delete_zaak_document(zaak_url: str) -> None:
    zaak_document = get_zaak_document(zaak_url)
    if zaak_document:
        zaak_document.delete()

    return


def create_zaaktype_document(zaaktype: ZaakType) -> ZaakTypeDocument:
    zaaktype_document = ZaakTypeDocument(
        url=zaaktype.url,
        omschrijving=zaaktype.omschrijving,
        catalogus=zaaktype.catalogus,
        identificatie=zaaktype.identificatie,
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
    if zaak.status:
        zaak.status = get_status(zaak) if isinstance(zaak.status, str) else zaak.status
        status_document = create_status_document(zaak.status)
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


def create_zaakinformatieobject_document(
    zio: ZaakInformatieObject,
) -> ZaakObjectDocument:
    return ZaakObjectDocument(url=zio.url, informatieobject=zio.informatieobject)


def update_zaakinformatieobjecten_in_zaak_document(zaak: Zaak) -> None:
    zaak.zaakinformatieobjecten = get_zaak_informatieobjecten(zaak)
    zaak_document = _get_zaak_document(zaak.uuid, zaak.url, create_zaak=zaak)
    zaak_document.zaakinformatieobjecten = [
        create_zaakinformatieobject_document(zio) for zio in zaak.zaakinformatieobjecten
    ]
    zaak_document.save()

    return


###################################################
#                    OBJECTEN                     #
###################################################


def _get_object_document(
    uuid: str, object_url: str, create_object: Optional[Dict] = None
) -> Optional[ObjectDocument]:
    try:
        object_document = ObjectDocument.get(id=uuid)
    except exceptions.NotFoundError as exc:
        logger.warning("object %s hasn't been indexed in ES", object_url, exc_info=True)
        if create_object:
            object_document = create_object_document(create_object)
            object_document.save()
        else:
            return

    return object_document


def create_objecttype_document(objecttype: Dict) -> ObjectTypeDocument:
    return ObjectTypeDocument(url=objecttype["url"], name=objecttype["name"])


def create_object_document(object: Dict) -> ObjectDocument:
    return ObjectDocument(
        meta={"id": object["uuid"]},
        url=object["url"],
        record_data=object["record"]["data"],
    )


def update_object_document(object: Dict) -> ObjectDocument:
    object_document = _get_object_document(
        object["uuid"], object["url"], create_object=object
    )
    object_document.update(
        refresh=True,
        record_data=object["record"]["data"],
    )
    return object_document


def delete_object_document(object_url: str) -> None:
    object_document = _get_object_document(_get_uuid_from_url(object_url), object_url)
    object_document.delete()


def create_related_zaak_document(
    related_zaak: Union[ZaakDocument, Zaak]
) -> RelatedZaakDocument:
    if isinstance(related_zaak.zaaktype, str):
        related_zaak.zaaktype = fetch_zaaktype(related_zaak.zaaktype)

    return RelatedZaakDocument(
        url=related_zaak.url,
        bronorganisatie=related_zaak.bronorganisatie,
        omschrijving=related_zaak.omschrijving,
        identificatie=related_zaak.identificatie,
        zaaktype=create_zaaktype_document(related_zaak.zaaktype),
        va_order=VA_ORDER[related_zaak.vertrouwelijkheidaanduiding],
    )


def update_related_zaken_in_object_document(object_url: str) -> None:
    # Get zaken information from zaken index
    zaakobjecten = get_zaakobjecten_related_to_object(object_url)

    def _get_zaak(url: str) -> Zaak:
        return get_zaak(zaak_url=url)

    with parallel() as executor:
        zaken = list(executor.map(_get_zaak, [zo.zaak for zo in zaakobjecten]))

    # resolve zaaktypen
    zaaktypen = {zt.url: zt for zt in get_zaaktypen()}

    for zaak in zaken:
        zaak.zaaktype = zaaktypen[zaak.zaaktype]

    # Fetch object document to be updated
    object = fetch_object(object_url)
    object_document = _get_object_document(
        object["uuid"], object_url, create_object=object
    )

    # Create related_zaak documenten and update object document
    related_zaken = [create_related_zaak_document(zaak) for zaak in zaken]
    object_document.related_zaken = related_zaken
    object_document.save()
    return


def update_related_zaak_in_object_documents(zaak: Zaak) -> None:
    objects = (
        ObjectDocument.search()
        .query(
            Nested(
                path="related_zaken",
                query=Bool(filter=[Term(related_zaken__url=zaak.url)]),
            )
        )
        .execute()
    )
    related_zaak = create_related_zaak_document(zaak)
    for obj in objects:
        related_zaken = [rz for rz in obj.related_zaken if rz.url != zaak.url]
        related_zaken.append(related_zaak)
        object_document = ObjectDocument.get(id=obj.meta.id)
        object_document.related_zaken = related_zaken
        object_document.save()

    return


###################################################
#                   DOCUMENTEN                    #
###################################################


def _get_informatieobject_document(
    informatieobject_url: str, create_informatieobject: Optional[Document] = None
) -> Optional[InformatieObjectDocument]:
    try:
        informatieobject_document = InformatieObjectDocument.get(
            id=_get_uuid_from_url(informatieobject_url)
        )
    except exceptions.NotFoundError as exc:
        logger.warning(
            "informatieobject %s hasn't been indexed in ES",
            informatieobject_url,
            exc_info=True,
        )
        if create_informatieobject:
            informatieobject_document = create_informatieobject_document(
                create_informatieobject
            )
            informatieobject_document.save()
        else:
            return

    return informatieobject_document


def create_informatieobject_document(
    document: Document,
) -> InformatieObjectDocument:
    return InformatieObjectDocument(
        meta={"id": _get_uuid_from_url(document.url)},
        url=document.url,
        titel=document.titel,
    )


def update_informatieobject_document(document: Document) -> InformatieObjectDocument:
    informatieobject_document = _get_informatieobject_document(
        document.url, create_informatieobject=document
    )
    informatieobject_document.update(refresh=True, titel=document.titel)
    return informatieobject_document


def delete_informatieobject_document(document_url: str) -> None:
    informatieobject_document = _get_informatieobject_document(document_url)
    informatieobject_document.delete()


def update_related_zaken_in_informatieobject_document(
    informatieobject_url: str,
) -> None:
    # Get zaken information from zaken index
    zios = get_zaakinformatieobjecten_related_to_informatieobject(informatieobject_url)

    def _get_zaak(url: str) -> Zaak:
        return get_zaak(zaak_url=url)

    with parallel() as executor:
        zaken = list(executor.map(_get_zaak, list({zio.zaak for zio in zios})))

    # resolve zaaktypen
    zaaktypen = {zt.url: zt for zt in get_zaaktypen()}

    for zaak in zaken:
        zaak.zaaktype = zaaktypen[zaak.zaaktype]

    # Fetch object document to be updated
    informatieobject = get_document(informatieobject_url)
    informatieobject_document = _get_informatieobject_document(
        informatieobject_url, create_informatieobject=informatieobject
    )

    # Create related_zaak documenten and update object document
    related_zaken = [create_related_zaak_document(zaak) for zaak in zaken]
    informatieobject_document.related_zaken = related_zaken
    informatieobject_document.save()
    return


def update_related_zaak_in_informatieobject_documents(zaak: Zaak) -> None:
    ios = (
        InformatieObjectDocument.search()
        .query(
            Nested(
                path="related_zaken",
                query=Bool(filter=[Term(related_zaken__url=zaak.url)]),
            )
        )
        .execute()
    )
    related_zaak = create_related_zaak_document(zaak)
    for io in ios:
        related_zaken = [rz for rz in io.related_zaken if rz.url != zaak.url]
        related_zaken.append(related_zaak)
        object_document = InformatieObjectDocument.get(id=io.meta.id)
        object_document.related_zaken = related_zaken
        object_document.save()

    return
