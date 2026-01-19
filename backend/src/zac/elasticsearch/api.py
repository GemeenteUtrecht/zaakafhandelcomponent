import logging
from collections import defaultdict
from typing import Dict, List, Optional, Tuple, Union

from django.conf import settings

from elasticsearch import exceptions
from elasticsearch_dsl.query import Bool, Nested, Term
from zgw_consumers.api_models.catalogi import InformatieObjectType, StatusType, ZaakType
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.api_models.zaken import Status, ZaakEigenschap, ZaakObject
from zgw_consumers.concurrent import parallel

from zac.accounts.datastructures import VA_ORDER
from zac.core.rollen import Rol
from zac.core.services import (
    fetch_latest_audit_trail_data_document,
    fetch_object,
    fetch_zaaktype,
    get_document,
    get_informatieobjecttype,
    get_rollen,
    get_status,
    get_statustype,
    get_zaak,
    get_zaakeigenschappen,
    get_zaakinformatieobjecten_related_to_informatieobject,
    get_zaakobjecten_related_to_object,
    get_zaaktypen,
)
from zgw.models.zrc import Zaak, ZaakInformatieObject

from .documents import (
    InformatieObjectDocument,
    InformatieObjectTypeDocument,
    ObjectDocument,
    ObjectTypeDocument,
    RelatedZaakDocument,
    RolDocument,
    StatusDocument,
    ZaakDocument,
    ZaakInformatieObjectDocument,
    ZaakObjectDocument,
    ZaakTypeDocument,
)

logger = logging.getLogger(__name__)


def _get_uuid_from_url(url: str) -> str:
    return url.strip("/").split("/")[-1]


###################################################
#                  Zaken index                    #
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
        refresh="wait_for",
    )

    return zaak_document


def _get_zaak_document(
    zaak_uuid: str, zaak_url: str, create_zaak: Optional[Zaak] = None
) -> Optional[ZaakDocument]:
    try:
        zaak_document = ZaakDocument.get(id=zaak_uuid)
    except exceptions.NotFoundError as exc:
        logger.warning("zaak %s hasn't been indexed in ES", zaak_url)
        if not create_zaak:
            return
        else:
            zaak_document = create_zaak_document(create_zaak)
            zaak_document.save(refresh="wait_for")

    return zaak_document


def get_zaak_document(zaak_url: str):
    zaak_uuid = _get_uuid_from_url(zaak_url)
    return _get_zaak_document(zaak_uuid, zaak_url)


def update_zaak_document(zaak: Zaak) -> ZaakDocument:
    zaak_document = _get_zaak_document(zaak.uuid, zaak.url, create_zaak=zaak)

    # Don't include zaaktype and identificatie since they are immutable.
    # Don't include status or objecten as those are handled through a
    # different handler in the notifications api.
    body = {
        "doc": {
            "bronorganisatie": zaak.bronorganisatie,
            "vertrouwelijkheidaanduiding": zaak.vertrouwelijkheidaanduiding,
            "va_order": VA_ORDER[zaak.vertrouwelijkheidaanduiding],
            "startdatum": zaak.startdatum,
            "einddatum": zaak.einddatum,
            "registratiedatum": zaak.registratiedatum,
            "deadline": zaak.deadline,
            "toelichting": zaak.toelichting,
            "zaakgeometrie": zaak.zaakgeometrie,
            "omschrijving": zaak.omschrijving,
            "identificatie_suggest": zaak.identificatie,
        }
    }
    zaak_document._get_connection().update(
        zaak_document.Index().name,
        zaak_document.meta.id,
        body,
        refresh="wait_for",
        retry_on_conflict=settings.ES_RETRY_ON_CONFLICT,
    )
    return zaak_document


def delete_zaak_document(zaak_url: str) -> None:
    zaak_document = get_zaak_document(zaak_url)
    if zaak_document:
        zaak_document.delete()

    return


def create_zaaktype_document(zaaktype: ZaakType) -> ZaakTypeDocument:
    from zac.core.services import fetch_catalogus

    catalogus = fetch_catalogus(zaaktype.catalogus)

    zaaktype_document = ZaakTypeDocument(
        url=zaaktype.url,
        omschrijving=zaaktype.omschrijving,
        catalogus=zaaktype.catalogus,
        catalogus_domein=catalogus.domein,
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
        if zaak.status.statustype.is_eindstatus:
            zaak_document.has_eindstatus = True
        else:
            zaak_document.has_eindstatus = False
        zaak_document.save(refresh="wait_for")

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
    zaak_document.save(refresh="wait_for")
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
    zaak.eigenschappen = get_zaakeigenschappen(zaak)
    eigenschappen_doc = create_eigenschappen_document(zaak.eigenschappen)

    zaak_document = _get_zaak_document(zaak.uuid, zaak.url, create_zaak=zaak)
    zaak_document.eigenschappen = eigenschappen_doc
    zaak_document.save(refresh="wait_for")
    return


###################################################
#                zaakobject index                 #
###################################################


def _get_zo_document(
    zo_uuid: str, zo_url: str, create_zo: Optional[ZaakObject] = None
) -> Optional[ZaakDocument]:
    try:
        zo_document = ZaakObjectDocument.get(id=zo_uuid)
    except exceptions.NotFoundError as exc:
        logger.warning("ZIO %s hasn't been indexed in ES", zo_url)
        if not create_zo:
            return
        else:
            zo_document = create_zaakobject_document(create_zo)
            zo_document.save(refresh="wait_for")

    return zo_document


def get_zaakobject_document(zo_url: str):
    zo_uuid = _get_uuid_from_url(zo_url)
    return _get_zo_document(zo_uuid, zo_url)


def create_zaakobject_document(
    zaakobject: ZaakObject,
) -> ZaakObjectDocument:
    return ZaakObjectDocument(
        meta={"id": zaakobject.uuid},
        url=zaakobject.url,
        object=zaakobject.object,
        zaak=zaakobject.zaak,
    )


###################################################
#           zaakinformatieobject index            #
###################################################


def _get_zio_document(
    zio_uuid: str, zio_url: str, create_zio: Optional[ZaakInformatieObject] = None
) -> Optional[ZaakInformatieObjectDocument]:
    try:
        zio_document = ZaakInformatieObjectDocument.get(id=zio_uuid)
    except exceptions.NotFoundError as exc:
        logger.warning("ZIO %s hasn't been indexed in ES", zio_url)
        if not create_zio:
            return
        else:
            zio_document = create_zaakinformatieobject_document(create_zio)
            zio_document.save(refresh="wait_for")

    return zio_document


def get_zaakinformatieobject_document(zio_url: str):
    zio_uuid = _get_uuid_from_url(zio_url)
    return _get_zio_document(zio_uuid, zio_url)


def update_zaakinformatieobject_document(
    zio: ZaakInformatieObject,
) -> ZaakInformatieObjectDocument:
    ziod = _get_zio_document(zio.uuid, zio.url, create_zio=zio)

    # Don't include zaaktype and identificatie since they are immutable.
    # Don't include status or objecten as those are handled through a
    # different handler in the notifications api.
    body = {
        "doc": {
            "informatieobject": zio.informatieobject,
            "zaak": zio.zaak,
        }
    }
    ziod._get_connection().update(
        ziod.Index().name,
        ziod.meta.id,
        body,
        refresh="wait_for",
        retry_on_conflict=settings.ES_RETRY_ON_CONFLICT,
    )
    return ziod


def create_zaakinformatieobject_document(
    zio: ZaakInformatieObject,
) -> ZaakInformatieObjectDocument:
    return ZaakInformatieObjectDocument(
        meta={"id": zio.uuid},
        url=zio.url,
        informatieobject=zio.informatieobject,
        zaak=zio.zaak,
    )


###################################################
#                    OBJECTEN                     #
###################################################


def _get_object_document(
    uuid: str, object_url: str, create_object: Optional[Dict] = None
) -> Optional[ObjectDocument]:
    try:
        object_document = ObjectDocument.get(id=uuid)
    except exceptions.NotFoundError as exc:
        logger.warning("object %s hasn't been indexed in ES", object_url)
        if create_object:
            object_document = create_object_document(create_object)
            object_document.save(refresh="wait_for")
        else:
            return

    return object_document


def create_objecttype_document(objecttype: Dict) -> ObjectTypeDocument:
    return ObjectTypeDocument(url=objecttype["url"], name=objecttype["name"])


def create_object_document(object: Dict) -> ObjectDocument:
    object_document = ObjectDocument(
        meta={"id": object["uuid"]},
        url=object["url"],
        record_data=object["record"]["data"],
        string_representation=object["stringRepresentation"],
        refresh="wait_for",
    )
    return object_document


def update_object_document(object: Dict) -> ObjectDocument:
    object_document = _get_object_document(
        object["uuid"], object["url"], create_object=object
    )
    body = {
        "doc": {
            "record_data": object["record"]["data"],
            "string_representation": object["stringRepresentation"],
        }
    }
    object_document._get_connection().update(
        object_document.Index().name,
        object_document.meta.id,
        body,
        refresh="wait_for",
        retry_on_conflict=settings.ES_RETRY_ON_CONFLICT,
    )
    return object_document


def delete_object_document(object_url: str) -> None:
    object_document = _get_object_document(_get_uuid_from_url(object_url), object_url)
    object_document.delete()


def create_related_zaak_document(
    related_zaak: Union[ZaakDocument, Zaak],
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

    with parallel(max_workers=settings.MAX_WORKERS) as executor:
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
    object_document.save(refresh="wait_for")
    return


def update_related_zaak_in_object_documents(zaak: Zaak) -> None:
    # check if related_zaak really changed before indexing bunch of documents
    related_zaak = create_related_zaak_document(zaak)

    object = (
        ObjectDocument.search()
        .query(
            Nested(
                path="related_zaken",
                query=Bool(filter=[Term(related_zaken__url=zaak.url)]),
            )
        )
        .extra(size=1)
        .execute()
    )
    changed = False
    if object and related_zaak.url in [z.url for z in object[0].related_zaken]:
        old_rz = [rz for rz in object[0].related_zaken if rz.url == related_zaak.url][0]
        if any(
            [
                old_rz.omschrijving != related_zaak.omschrijving,
                old_rz.va_order != related_zaak.va_order,
            ]
        ):
            changed = True

    if changed:
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
        for obj in objects:
            related_zaken = [rz for rz in obj.related_zaken if rz.url != zaak.url]
            related_zaken.append(related_zaak)
            object_document = ObjectDocument.get(id=obj.meta.id)
            object_document.related_zaken = related_zaken
            object_document.save(refresh="wait_for")
    return


###################################################
#                   DOCUMENTEN                    #
###################################################


def create_iot_document(iot: InformatieObjectType) -> InformatieObjectTypeDocument:
    return InformatieObjectTypeDocument(
        url=iot.url,
        catalogus=iot.catalogus,
        omschrijving=iot.omschrijving,
        vertrouwelijkheidaanduiding=iot.vertrouwelijkheidaanduiding,
        begin_geldigheid=iot.begin_geldigheid,
        einde_geldigheid=iot.einde_geldigheid,
        concept=iot.concept,
    )


def resolve_iot_for_document(io: Document) -> InformatieObjectTypeDocument:
    # resolve iot if necessary
    if type(io.informatieobjecttype) == str:
        io.informatieobjecttype = get_informatieobjecttype(io.informatieobjecttype)

    if isinstance(io.informatieobjecttype, InformatieObjectType):
        return create_iot_document(io.informatieobjecttype)

    raise RuntimeError(f"Can't turn io.informatieobjecttype into InformatieObjectType.")


def _get_informatieobject_document(
    informatieobject_url: str, create_informatieobject: Optional[Document] = None
) -> Tuple[bool, Optional[InformatieObjectDocument]]:
    created = False
    try:
        informatieobject_document = InformatieObjectDocument.get(
            id=_get_uuid_from_url(informatieobject_url)
        )
    except exceptions.NotFoundError as exc:
        logger.warning(
            "informatieobject %s is not indexed in ES.",
            informatieobject_url,
        )
        if create_informatieobject:
            informatieobject_document = create_informatieobject_document(
                create_informatieobject
            )
            informatieobject_document.save(refresh="wait_for")
            created = True
        else:
            return created, None

    return created, informatieobject_document


def create_informatieobject_document(
    document: Document,
) -> InformatieObjectDocument:

    if not hasattr(document, "last_edited_date"):
        at = fetch_latest_audit_trail_data_document(document.url)
        document.last_edited_date = at.last_edited_date if at else None

    iod = InformatieObjectDocument(
        meta={"id": document.uuid},
        auteur=document.auteur,
        beschrijving=document.beschrijving,
        bestandsnaam=document.bestandsnaam,
        bestandsomvang=document.bestandsomvang,
        bronorganisatie=document.bronorganisatie,
        creatiedatum=document.creatiedatum,
        formaat=document.formaat,
        identificatie=document.identificatie,
        indicatie_gebruiksrecht=document.indicatie_gebruiksrecht,
        informatieobjecttype=resolve_iot_for_document(document).to_dict(),
        inhoud=document.inhoud,
        integriteit=document.integriteit,
        last_edited_date=document.last_edited_date,
        link=document.link,
        locked=document.locked,
        ondertekening=document.ondertekening,
        ontvangstdatum=document.ontvangstdatum,
        status=document.status,
        taal=document.taal,
        titel=document.titel,
        url=document.url,
        versie=document.versie,
        vertrouwelijkheidaanduiding=document.vertrouwelijkheidaanduiding,
        verzenddatum=document.verzenddatum,
        refresh="wait_for",
    )
    return iod


def update_informatieobject_document(document: Document) -> InformatieObjectDocument:
    created, informatieobject_document = _get_informatieobject_document(
        document.url, create_informatieobject=document
    )

    if not created:
        # get latest edit date
        at = fetch_latest_audit_trail_data_document(document.url)
        body = {
            "doc": {
                "auteur": document.auteur,
                "beschrijving": document.beschrijving,
                "bestandsnaam": document.bestandsnaam,
                "bestandsomvang": document.bestandsomvang,
                "bronorganisatie": document.bronorganisatie,
                "creatiedatum": document.creatiedatum,
                "formaat": document.formaat,
                "identificatie": document.identificatie,
                "indicatie_gebruiksrecht": document.indicatie_gebruiksrecht,
                "informatieobjecttype": resolve_iot_for_document(document).to_dict(),
                "inhoud": document.inhoud,
                "integriteit": document.integriteit,
                "last_edited_date": at.last_edited_date if at else None,
                "link": document.link,
                "locked": document.locked,
                "ondertekening": document.ondertekening,
                "ontvangstdatum": document.ontvangstdatum,
                "status": document.status,
                "taal": document.taal,
                "titel": document.titel,
                "url": document.url,
                "versie": document.versie,
                "vertrouwelijkheidaanduiding": document.vertrouwelijkheidaanduiding,
                "verzenddatum": document.verzenddatum,
            }
        }
        informatieobject_document._get_connection().update(
            informatieobject_document.Index().name,
            informatieobject_document.meta.id,
            body,
            refresh="wait_for",
            retry_on_conflict=settings.ES_RETRY_ON_CONFLICT,
        )
    return informatieobject_document


def delete_informatieobject_document(document_url: str) -> None:
    created, informatieobject_document = _get_informatieobject_document(document_url)
    informatieobject_document.delete()


def update_related_zaken_in_informatieobject_document(
    informatieobject_url: str,
) -> None:
    # Get zaken information from zaken index
    zios = get_zaakinformatieobjecten_related_to_informatieobject(informatieobject_url)

    def _get_zaak(url: str) -> Zaak:
        return get_zaak(zaak_url=url)

    with parallel(max_workers=settings.MAX_WORKERS) as executor:
        zaken = list(executor.map(_get_zaak, list({zio.zaak for zio in zios})))

    # resolve zaaktypen
    zaaktypen = {zt.url: zt for zt in get_zaaktypen()}

    for zaak in zaken:
        zaak.zaaktype = zaaktypen[zaak.zaaktype]

    # Fetch object document to be updated
    informatieobject = get_document(informatieobject_url)
    created, informatieobject_document = _get_informatieobject_document(
        informatieobject_url, create_informatieobject=informatieobject
    )

    # Create related_zaak documenten and update object document
    related_zaken = [create_related_zaak_document(zaak) for zaak in zaken]
    informatieobject_document.related_zaken = related_zaken
    informatieobject_document.save(refresh="wait_for")
    return


def update_related_zaak_in_informatieobject_documents(zaak: Zaak) -> None:
    # Check if related_zaak really changed before indexing all relevant
    # documents
    related_zaak = create_related_zaak_document(zaak)
    io = (
        InformatieObjectDocument.search()
        .query(
            Nested(
                path="related_zaken",
                query=Bool(filter=[Term(related_zaken__url=zaak.url)]),
            )
        )
        .extra(size=1)
        .execute()
    )

    changed = False
    if io and related_zaak.url in [z.url for z in io[0].related_zaken]:
        old_rz = [rz for rz in io[0].related_zaken if rz.url == related_zaak.url][0]
        if any(
            [
                old_rz.omschrijving != related_zaak.omschrijving,
                old_rz.va_order != related_zaak.va_order,
            ]
        ):
            changed = True

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
    if changed:
        for io in ios:
            related_zaken = [rz for rz in io.related_zaken if rz.url != zaak.url]
            related_zaken.append(related_zaak)
            object_document = InformatieObjectDocument.get(id=io.meta.id)
            object_document.related_zaken = related_zaken
            object_document.save(refresh="wait_for")

    return
