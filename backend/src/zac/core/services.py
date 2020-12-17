import asyncio
import base64
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urljoin

from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.uploadedfile import UploadedFile
from django.utils import timezone

import aiohttp
import requests
from furl import furl
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.besluiten import Besluit, BesluitDocument
from zgw_consumers.api_models.catalogi import (
    BesluitType,
    Eigenschap,
    ResultaatType,
    RolType,
    ZaakType,
)
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.api_models.zaken import Resultaat, Status, ZaakEigenschap, ZaakObject
from zgw_consumers.concurrent import parallel
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.service import get_paginated_results

from zac.accounts.permissions import UserPermissions
from zac.contrib.brp.models import BRPConfig
from zac.elasticsearch.searches import SUPPORTED_QUERY_PARAMS, search
from zac.utils.decorators import cache as cache_result
from zgw.models import InformatieObjectType, StatusType, Zaak

from ..accounts.models import User
from .cache import get_zios_cache_key, invalidate_document_cache, invalidate_zaak_cache
from .models import CoreConfig
from .permissions import zaken_inzien
from .rollen import Rol

logger = logging.getLogger(__name__)

AN_HOUR = 60 * 60
A_DAY = AN_HOUR * 24


def _client_from_url(url: str):
    service = Service.get_service(url)
    return service.build_client()


def _client_from_object(obj):
    return _client_from_url(obj.url)


async def fetch(session: aiohttp.ClientSession, url: str):
    creds = _client_from_url(url).auth.credentials()
    async with session.get(url, headers=creds) as response:
        return await response.json()


def fetch_async(cache_key: str, job, *args, **kwargs):
    result = cache.get(cache_key)
    if result is not None:
        return result

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    coro = job(*args, **kwargs)
    result = loop.run_until_complete(coro)
    cache.set(cache_key, result, 30 * 60)
    return result


###################################################
#                       ZTC                       #
###################################################


@cache_result("besluittype:{url}", timeout=A_DAY)
def fetch_besluittype(url: str) -> BesluitType:
    client = _client_from_url(url)
    result = client.retrieve("besluittype", url=url)
    return factory(BesluitType, result)


def _get_from_catalogus(resource: str, catalogus: str = "", **extra_query) -> List:
    """
    Retrieve informatieobjecttype or zaaktypen from all catalogi in the configured APIs.
    """
    query_params = {"catalogus": catalogus} if catalogus else {}
    query_params.update(**extra_query)
    ztcs = Service.objects.filter(api_type=APITypes.ztc)

    if catalogus:
        clients = [_client_from_url(catalogus)]
    else:
        clients = [ztc.build_client() for ztc in ztcs]

    result = []
    for client in clients:
        result += get_paginated_results(client, resource, query_params=query_params)

    return result


@cache_result("zaaktypen:{catalogus}", timeout=AN_HOUR)
def _get_zaaktypen(catalogus: str = "") -> List[ZaakType]:
    """
    Retrieve all the zaaktypen from all catalogi in the configured APIs.
    """
    results = _get_from_catalogus(resource="zaaktype", catalogus=catalogus)
    return factory(ZaakType, results)


@cache_result("informatieobjecttype:{catalogus}", timeout=AN_HOUR)
def get_informatieobjecttypen(catalogus: str = "") -> List[InformatieObjectType]:
    """
    Retrieve all the specified informatieobjecttypen from all catalogi in the configured APIs.
    """
    results = _get_from_catalogus(resource="informatieobjecttype", catalogus=catalogus)
    return factory(InformatieObjectType, results)


def get_zaaktypen(
    user_perms: Optional[UserPermissions] = None, catalogus: str = ""
) -> List[ZaakType]:
    zaaktypen = _get_zaaktypen(catalogus=catalogus)
    if user_perms is not None:
        # filter out zaaktypen from permissions
        zaaktypen = user_perms.filter_zaaktypen(zaaktypen)
    return zaaktypen


@cache_result("zaaktype:{url}", timeout=A_DAY)
def fetch_zaaktype(url: str) -> ZaakType:
    client = _client_from_url(url)
    result = client.retrieve("zaaktype", url=url)
    return factory(ZaakType, result)


@cache_result("zt:statustypen:{zaaktype.url}", timeout=A_DAY)
def get_statustypen(zaaktype: ZaakType) -> List[StatusType]:
    client = _client_from_object(zaaktype)
    _statustypen = get_paginated_results(
        client, "statustype", query_params={"zaaktype": zaaktype.url}
    )
    statustypen = factory(StatusType, _statustypen)
    return statustypen


@cache_result("statustype:{url}", timeout=A_DAY)
def get_statustype(url: str) -> StatusType:
    client = _client_from_url(url)
    status_type = client.retrieve("statustype", url=url)
    status_type = factory(StatusType, status_type)
    return status_type


@cache_result("zt:resultaattypen:{zaaktype.url}", timeout=A_DAY)
def get_resultaattypen(zaaktype: ZaakType) -> List[ResultaatType]:
    client = _client_from_object(zaaktype)
    resultaattypen = get_paginated_results(
        client,
        "resultaattype",
        query_params={"zaaktype": zaaktype.url},
    )

    resultaattypen = factory(ResultaatType, resultaattypen)

    # resolve relations
    for resultaattype in resultaattypen:
        resultaattype.zaaktype = zaaktype

    return resultaattypen


@cache_result("zt:eigenschappen:{zaaktype.url}", timeout=A_DAY)
def get_eigenschappen(zaaktype: ZaakType) -> List[Eigenschap]:
    client = _client_from_object(zaaktype)
    eigenschappen = get_paginated_results(
        client,
        "eigenschap",
        query_params={"zaaktype": zaaktype.url},
    )

    eigenschappen = factory(Eigenschap, eigenschappen)

    # resolve relations
    for eigenschap in eigenschappen:
        eigenschap.zaaktype = zaaktype

    return eigenschappen


@cache_result("roltype:{url}", timeout=A_DAY)
def get_roltype(url: str) -> RolType:
    client = _client_from_url(url)
    result = client.retrieve("roltype", url)
    return factory(RolType, result)


@cache_result("zt:roltypen:{zaaktype.url}:{omschrijving_generiek}", timeout=A_DAY)
def get_roltypen(zaaktype: ZaakType, omschrijving_generiek: str = "") -> list:
    query_params = {"zaaktype": zaaktype.url}
    if omschrijving_generiek:
        query_params.update({"omschrijvingGeneriek": omschrijving_generiek})
    client = _client_from_object(zaaktype)
    roltypen = get_paginated_results(client, "roltype", query_params=query_params)

    roltypen = factory(RolType, roltypen)

    # resolve relations
    for roltype in roltypen:
        roltype.zaaktype = zaaktype

    return roltypen


@cache_result("ziot:{zaaktype.url}", timeout=A_DAY)
def get_informatieobjecttypen_for_zaaktype(
    zaaktype: ZaakType,
) -> List[InformatieObjectType]:
    """
    Retrieve all informatieobjecttypen relevant for a given zaaktype.
    """
    client = _client_from_object(zaaktype)
    results = get_paginated_results(
        client, "zaakinformatieobjecttype", query_params={"zaaktype": zaaktype.url}
    )
    with parallel() as executor:
        urls = [
            iot["informatieobjecttype"]
            for iot in sorted(results, key=lambda iot: iot["volgnummer"])
        ]
        results = executor.map(get_informatieobjecttype, urls)
    return list(results)


@cache_result("informatieobjecttype:{url}", timeout=A_DAY)
def get_informatieobjecttype(url: str) -> InformatieObjectType:
    client = _client_from_url(url)
    data = client.retrieve("informatieobjecttype", url=url)
    return factory(InformatieObjectType, data)


@cache_result("zt:besluittypen:{zaaktype.url}")
def get_besluittypen_for_zaaktype(zaaktype: ZaakType) -> List[BesluitType]:
    with parallel() as executor:
        results = executor.map(fetch_besluittype, zaaktype.besluittypen)
    return list(results)


###################################################
#                       ZRC                       #
###################################################


# @cache_result(
#     "zaken:{client.base_url}:{zaaktype}:{max_va}:{identificatie}:{bronorganisatie}:{extra_query}",
#     timeout=AN_HOUR,
# )
def _find_zaken(
    client,
    zaaktype: str = "",
    identificatie: str = "",
    bronorganisatie: str = "",
    max_va: str = "",
    find_all=False,
    **extra_query,
) -> List[Dict]:
    """
    Retrieve zaken for a particular client with filter parameters.
    """
    extra_query.pop("skip_cache", None)

    query = {
        "zaaktype": zaaktype,
        "identificatie": identificatie,
        "bronorganisatie": bronorganisatie,
        "maximaleVertrouwelijkheidaanduiding": max_va,
        **extra_query,
    }
    logger.debug("Querying zaken with %r", query)
    minimum = None if find_all else 25
    _zaken = get_paginated_results(
        client,
        "zaak",
        query_params=query,
        minimum=minimum,
    )
    return _zaken


def get_allowed_kwargs(user_perms: UserPermissions) -> list:
    if user_perms.user.is_superuser:
        return []

    relevant_perms = [
        perm
        for perm in user_perms.zaaktype_permissions
        if perm.permission == zaken_inzien.name
    ]

    find_kwargs = [
        {
            "zaaktypen": [zaaktype.url for zaaktype in perm.zaaktypen],
            "max_va": perm.max_va,
            "oo": perm.oo,
        }
        for perm in relevant_perms
    ]

    return find_kwargs


def get_zaken_es(
    user_perms: UserPermissions,
    size=None,
    query_params=None,
) -> List[Zaak]:
    """
    Fetch all zaken from the ZRCs.

    Only retrieve what the user is allowed to see.
    """
    find_kwargs = query_params or {}
    # validate query params
    not_supported_params = set(find_kwargs.keys()) - set(SUPPORTED_QUERY_PARAMS)
    if not_supported_params:
        raise ValueError(
            "{} parameters are not supported for ES-based search".format(
                not_supported_params
            )
        )

    allowed_kwargs = get_allowed_kwargs(user_perms)
    if not user_perms.user.is_superuser and not allowed_kwargs:
        return []

    find_kwargs["allowed"] = allowed_kwargs

    _base_zaaktypen = {zt.url: zt for zt in get_zaaktypen(user_perms)}

    # ES search
    zaak_urls = search(size=size, **find_kwargs)

    def _get_zaak(zaak_url):
        return get_zaak(zaak_url=zaak_url)

    with parallel(max_workers=10) as executor:
        results = executor.map(_get_zaak, zaak_urls)
        zaken = list(results)

    # resolve zaaktype reference
    for zaak in zaken:
        zaak.zaaktype = _base_zaaktypen[zaak.zaaktype]

    return zaken


def get_zaken_all(
    **query_params,
) -> List[Zaak]:
    """
    Fetch all zaken from the ZRCs.
    Used to index Zaken in ES.
    Should not be used for searches with user permissions
    """

    zaaktypen = {zt.url: zt for zt in get_zaaktypen()}

    zrcs = Service.objects.filter(api_type=APITypes.zrc)
    clients = [zrc.build_client() for zrc in zrcs]

    def _get_paginated_results(client):
        return get_paginated_results(client, "zaak", query_params=query_params)

    with parallel() as executor:
        results = executor.map(_get_paginated_results, clients)
        flattened = sum(list(results), [])

    zaken = factory(Zaak, flattened)

    # resolve zaaktype reference
    for zaak in zaken:
        zaak.zaaktype = zaaktypen[zaak.zaaktype]

    # sort results by startdatum / registratiedatum / identificatie
    zaken = sorted(
        zaken,
        key=lambda zaak: (zaak.registratiedatum, zaak.startdatum, zaak.identificatie),
        reverse=True,
    )

    return zaken


def search_zaak_for_related_object(queries: List[dict], resource) -> List[Zaak]:
    zrcs = Service.objects.filter(api_type=APITypes.zrc)
    clients = [zrc.build_client() for zrc in zrcs]

    def _get_related_objects(client) -> list:
        related_objects = []
        for query in queries:
            related_objects += get_paginated_results(
                client, resource, query_params=query
            )
        return related_objects

    def _get_zaak(args):
        client, zaak_url = args
        return get_zaak(zaak_uuid=None, zaak_url=zaak_url, client=client)

    with parallel(max_workers=10) as executor:
        results = executor.map(_get_related_objects, clients)

        job_args = []
        for client, related_objects in zip(clients, results):
            zaak_urls = set(ro["zaak"] for ro in related_objects)
            job_args += [(client, zaak_url) for zaak_url in zaak_urls]
        zaken_results = executor.map(_get_zaak, job_args)

    zaken = list(zaken_results)

    def _resolve_zaaktype(zaak):
        zaak.zaaktype = fetch_zaaktype(zaak.zaaktype)

    with parallel(max_workers=10) as executor:
        for zaak in zaken:
            executor.submit(_resolve_zaaktype, zaak)

    return zaken


def search_zaken_for_object(object_url: str) -> List[Zaak]:
    """
    Query the ZRCs for zaken that have object_url as a zaakobject.
    """
    query = {"object": object_url}
    return search_zaak_for_related_object([query], "zaakobject")


def search_zaken_for_bsn(bsn: str) -> List[Zaak]:
    brp_config = BRPConfig.get_solo()
    service = brp_config.service

    queries = [
        {"betrokkeneIdentificatie__natuurlijkPersoon__inpBsn": bsn},
    ]

    if service:
        brp_url = urljoin(service.api_root, "ingeschrevenpersonen")
        queries += [
            {"betrokkene": f"{brp_url}/{bsn}"},
            {"betrokkene": f"{brp_url}?burgerservicenummer={bsn}"},
        ]

    return search_zaak_for_related_object(queries, "rol")


# TODO: listen for notifiations to invalidate cache OR look into ETag when it's available
@cache_result("zaak:{bronorganisatie}:{identificatie}", timeout=AN_HOUR / 2)
def find_zaak(bronorganisatie: str, identificatie: str) -> Zaak:
    """
    Find the Zaak, uniquely identified by bronorganisatie & identificatie.
    """
    query = {"bronorganisatie": bronorganisatie, "identificatie": identificatie}

    # try local search index first
    results = search(size=1, **query)
    if results:
        zaak = get_zaak(zaak_url=results[0])
    else:
        # not in cache -> check it in all known ZRCs
        zrcs = Service.objects.filter(api_type=APITypes.zrc)
        zaak = None
        for zrc in zrcs:
            client = zrc.build_client()
            results = get_paginated_results(client, "zaak", query_params=query)

            if not results:
                continue

            if len(results) > 1:
                logger.warning("Found multiple Zaken for query %r", query)

            # there's only supposed to be one unique case
            zaak = factory(Zaak, results[0])
            break

        if zaak is None:
            raise ObjectDoesNotExist(
                "Zaak object was not found in any known registrations"
            )

    # resolve relation
    zaak.zaaktype = fetch_zaaktype(zaak.zaaktype)

    return zaak


def get_statussen(zaak: Zaak) -> List[Status]:
    client = _client_from_object(zaak)

    # re-use cached objects
    statustypen = {st.url: st for st in get_statustypen(zaak.zaaktype)}

    # fetch the statusses
    _statussen = get_paginated_results(
        client, "status", query_params={"zaak": zaak.url}
    )

    statussen = factory(Status, _statussen)

    # convert URL references into objects
    for status in statussen:
        status.statustype = statustypen[status.statustype]
        status.zaak = zaak

    return sorted(statussen, key=lambda x: x.datum_status_gezet, reverse=True)


@cache_result("zaak-status:{zaak.status}", timeout=AN_HOUR)
def get_status(zaak: Zaak) -> Optional[Status]:
    if not zaak.status:
        return None
    assert isinstance(zaak.status, str), "Status already resolved."
    client = _client_from_object(zaak)
    _status = client.retrieve("status", url=zaak.status)

    # resolve statustype
    status = factory(Status, _status)
    status.statustype = get_statustype(_status["statustype"])
    return status


def get_zaak_eigenschappen(zaak: Zaak) -> List[ZaakEigenschap]:
    # the zaak object itself already contains a list of URL references
    if not zaak.eigenschappen:
        return []

    zrc_client = _client_from_object(zaak)
    eigenschappen = {
        eigenschap.url: eigenschap for eigenschap in get_eigenschappen(zaak.zaaktype)
    }

    zaak_eigenschappen = zrc_client.list("zaakeigenschap", zaak_uuid=zaak.uuid)
    zaak_eigenschappen = factory(ZaakEigenschap, zaak_eigenschappen)

    # resolve relations
    for zaak_eigenschap in zaak_eigenschappen:
        zaak_eigenschap.zaak = zaak
        zaak_eigenschap.eigenschap = eigenschappen[zaak_eigenschap.eigenschap]

    return zaak_eigenschappen


@cache_result("get_zaak:{zaak_uuid}:{zaak_url}", timeout=AN_HOUR)
def get_zaak(zaak_uuid=None, zaak_url=None, client=None) -> Zaak:
    """
    Retrieve zaak with uuid or url
    """
    if client is None and zaak_url is not None:
        client = _client_from_url(zaak_url)

    if client is None:
        zrcs = Service.objects.filter(api_type=APITypes.zrc)
        result = None

        for zrc in zrcs:
            client = zrc.build_client()
            result = client.retrieve("zaak", url=zaak_url, uuid=zaak_uuid)

            if not result:
                continue
    else:
        result = client.retrieve("zaak", url=zaak_url, uuid=zaak_uuid)

    result = factory(Zaak, result)

    if result is None:
        raise ObjectDoesNotExist("Zaak object was not found in any known registrations")

    return result


def get_related_zaken(zaak: Zaak) -> List[Tuple[str, Zaak]]:
    """
    return list of related zaken with selected zaaktypen
    """

    def _fetch_zaak(relevante_andere_zaak: dict) -> Tuple[str, Zaak]:
        zaak = get_zaak(zaak_url=relevante_andere_zaak["url"])
        # resolve relation(s)
        zaak.zaaktype = fetch_zaaktype(zaak.zaaktype)

        # resolve status & resultaat
        zaak.status = get_status(zaak)
        zaak.resultaat = get_resultaat(zaak)

        return relevante_andere_zaak["aard_relatie"], zaak

    with parallel() as executor:
        results = list(executor.map(_fetch_zaak, zaak.relevante_andere_zaken))

    return results


def get_zaakobjecten(zaak: Union[Zaak, str]) -> List[ZaakObject]:
    if isinstance(zaak, Zaak):
        zaak_url = zaak.url
    else:
        zaak_url = zaak

    client = _client_from_url(zaak_url)

    zaakobjecten = get_paginated_results(
        client,
        "zaakobject",
        query_params={"zaak": zaak_url},
    )

    return factory(ZaakObject, zaakobjecten)


def get_resultaat(zaak: Zaak) -> Optional[Resultaat]:
    if not zaak.resultaat:
        return None

    client = _client_from_object(zaak)
    resultaat = client.retrieve("resultaat", url=zaak.resultaat)

    resultaat = factory(Resultaat, resultaat)

    # resolve relations
    _resultaattypen = {rt.url: rt for rt in get_resultaattypen(zaak.zaaktype)}
    resultaat.zaak = zaak
    resultaat.resultaattype = _resultaattypen[resultaat.resultaattype]

    return resultaat


@cache_result("rollen:{zaak.url}", alias="request", timeout=10)
def get_rollen(zaak: Zaak) -> List[Rol]:
    # fetch the rollen
    client = _client_from_object(zaak)
    _rollen = get_paginated_results(client, "rol", query_params={"zaak": zaak.url})

    rollen = factory(Rol, _rollen)

    # convert URL references into objects
    for rol in rollen:
        rol.zaak = zaak

    return rollen


def get_zaak_informatieobjecten(zaak: Zaak) -> list:
    client = _client_from_object(zaak)
    zaak_informatieobjecten = client.list(
        "zaakinformatieobject", query_params={"zaak": zaak.url}
    )
    return zaak_informatieobjecten


def zet_resultaat(
    zaak: Zaak, resultaattype: ResultaatType, toelichting: str = ""
) -> Resultaat:
    assert (
        not zaak.resultaat
    ), "Can't set a new resultaat for a zaak, must delete the old one first"
    assert len(toelichting) <= 1000, "Toelichting is > 1000 characters"

    client = _client_from_object(zaak)
    resultaat = client.create(
        "resultaat",
        {
            "zaak": zaak.url,
            "resultaattype": resultaattype.url,
            "toelichting": toelichting,
        },
    )
    resultaat = factory(Resultaat, resultaat)

    # resolve relations
    resultaat.zaak = zaak
    resultaat.resultaattype = resultaattype
    zaak.resultaat = resultaat

    invalidate_zaak_cache(zaak)
    return resultaat


def zet_status(zaak: Zaak, statustype: StatusType, toelichting: str = "") -> Status:
    assert len(toelichting) <= 1000, "Toelichting is > 1000 characters"

    client = _client_from_object(zaak)
    status = client.create(
        "status",
        {
            "zaak": zaak.url,
            "statustype": statustype.url,
            "datumStatusGezet": timezone.now().isoformat(),
            "statustoelichting": toelichting,
        },
    )

    status = factory(Status, status)

    # resolve relations
    status.zaak = zaak
    status.statustype = statustype
    zaak.status = status

    invalidate_zaak_cache(zaak)
    return status


@cache_result("get_behandelaar_zaken:{user.username}", timeout=AN_HOUR)
def get_behandelaar_zaken(user: User) -> List[Zaak]:
    """
    Retrieve zaken where `user` is a medewerker in the role of behandelaar.
    """
    medewerker_id = user.username
    user_perms = UserPermissions(user)
    behandelaar_zaken = get_zaken_es(
        user_perms, query_params={"behandelaar": medewerker_id}
    )
    return behandelaar_zaken


def get_rollen_all() -> List[Rol]:
    """
    Retrieve all available rollen for ES indexing
    """
    zrcs = Service.objects.filter(api_type=APITypes.zrc)

    all_rollen = []
    for zrc in zrcs:
        client = zrc.build_client()

        _rollen = get_paginated_results(client, "rol")

        all_rollen += factory(Rol, _rollen)

    return all_rollen


###################################################
#                       DRC                       #
###################################################


def get_documenten(
    zaak: Zaak, doc_versions: Optional[Dict[str, int]] = None
) -> Tuple[List[Document], List[str]]:
    logger.debug("Retrieving documents linked to zaak %r", zaak)

    # get zaakinformatieobjecten
    zaak_informatieobjecten = get_zaak_informatieobjecten(zaak)

    # retrieve the documents themselves, in parallel
    zios = [zio["informatieobject"] for zio in zaak_informatieobjecten]
    cache_key = get_zios_cache_key(zios)

    logger.debug("Fetching %d documents", len(zaak_informatieobjecten))
    documenten = fetch_async(
        cache_key,
        fetch_documents,
        zaak_informatieobjecten,
        doc_versions=doc_versions,
    )

    logger.debug("Retrieving ZTC configuration for informatieobjecttypen")

    gone = []
    found = []
    for document, zio in zip(documenten, zaak_informatieobjecten):
        if "url" in document:  # resolved
            found.append(document)
            continue

        if document["status"] != 404:  # unknown error
            continue

        gone.append(zio["informatieobject"])

    # figure out relevant ztcs
    informatieobjecttypen = {document["informatieobjecttype"] for document in found}

    _iot = list(informatieobjecttypen)

    ztcs = Service.objects.filter(api_type=APITypes.ztc)
    relevant_ztcs = []
    for ztc in ztcs:
        if any(iot.startswith(ztc.api_root) for iot in _iot):
            relevant_ztcs.append(ztc)

    all_informatieobjecttypen = []
    for ztc in relevant_ztcs:
        client = ztc.build_client()
        results = get_paginated_results(client, "informatieobjecttype")
        all_informatieobjecttypen += [
            iot for iot in results if iot["url"] in informatieobjecttypen
        ]

    informatieobjecttypen = {
        raw["url"]: InformatieObjectType.from_raw(raw)
        for raw in all_informatieobjecttypen
    }

    documenten = factory(Document, found)

    # resolve relations
    for document in documenten:
        document.informatieobjecttype = informatieobjecttypen[
            document.informatieobjecttype
        ]

    # cache results
    for document in documenten:
        cache_key = f"document:{document.bronorganisatie}:{document.identificatie}"
        cache.set(cache_key, document, timeout=AN_HOUR / 2)

    return documenten, gone


@cache_result(
    "document:{bronorganisatie}:{identificatie}:{versie}", timeout=AN_HOUR / 2
)
def find_document(
    bronorganisatie: str, identificatie: str, versie: Optional[int] = None
) -> Document:
    """
    Find the document uniquely identified by bronorganisatie and identificatie.
    """
    query = {"bronorganisatie": bronorganisatie, "identificatie": identificatie}

    # not in cache -> check it in all known DRCs
    drcs = Service.objects.filter(api_type=APITypes.drc)
    for drc in drcs:
        client = drc.build_client()
        results = get_paginated_results(
            client, "enkelvoudiginformatieobject", query_params=query
        )

        if not results:
            continue

        # get the latest one if no explicit version is given
        if versie is None:
            result = sorted(results, key=lambda r: r["versie"], reverse=True)[0]
        else:
            # there's only supposed to be one unique case
            # NOTE: there are known issues with DRC-CMIS returning multiple docs for
            # the same version...
            candidates = [result for result in results if result["versie"] == versie]
            if not candidates:
                raise RuntimeError(
                    f"Version '{versie}' for document does not seem to exist..."
                )
            if len(candidates) > 1:
                logger.warning(
                    "Multiple results for version '%d' found, this is an error in the DRC "
                    "implementation!",
                    versie,
                    extra={"query": query},
                )

            result = candidates[0]

        result = factory(Document, result)
        break

    if result is None:
        raise ObjectDoesNotExist(
            "Document object was not found in any known registrations"
        )

    return result


@cache_result("get_document:{url}", timeout=AN_HOUR)
def get_document(url: str) -> Document:
    """
    Retrieve document by URL.
    """
    client = _client_from_url(url)
    result = client.retrieve("enkelvoudiginformatieobject", url=url)
    return factory(Document, result)


def download_document(document: Document) -> Tuple[Document, bytes]:
    client = _client_from_object(document)
    response = requests.get(document.inhoud, headers=client.auth.credentials())
    response.raise_for_status()
    return document, response.content


async def fetch_documents(zios: list, doc_versions: Optional[Dict[str, int]] = None):
    doc_versions = doc_versions or {}
    tasks = []
    async with aiohttp.ClientSession() as session:
        for zio in zios:
            document_furl = furl(zio["informatieobject"])
            if zio["informatieobject"] in doc_versions:
                document_furl.args["versie"] = doc_versions[zio["informatieobject"]]
            task = asyncio.ensure_future(fetch(session=session, url=document_furl.url))
            tasks.append(task)

        responses = await asyncio.gather(*tasks)

    return responses


def update_document(url: str, file: UploadedFile, data: dict):
    client = _client_from_url(url)

    # lock eio
    lock_result = client.operation(
        "enkelvoudiginformatieobject_lock", data={}, url=f"{url}/lock"
    )
    lock = lock_result["lock"]

    # update eio
    content = base64.b64encode(file.read()).decode("utf-8")
    data["inhoud"] = content
    data["bestandsomvang"] = file.size
    data["bestandsnaam"] = file.name
    data["lock"] = lock
    response = client.partial_update("enkelvoudiginformatieobject", data=data, url=url)

    document = factory(Document, response)

    # unlock
    client.request(
        f"{url}/unlock",
        "enkelvoudiginformatieobject_unlock",
        "POST",
        expected_status=204,
        json={"lock": lock},
    )
    # invalid cache
    invalidate_document_cache(document)

    # refresh new state
    document = get_document(document.url)
    return document


###################################################
#                       BRC                       #
###################################################


def get_besluiten(zaak: Zaak) -> List[Besluit]:
    query = {"zaak": zaak.url}
    brcs = Service.objects.filter(api_type=APITypes.brc)

    results = []
    for brc in brcs:
        client = brc.build_client()
        results += get_paginated_results(client, "besluit", query_params=query)

    besluiten = factory(Besluit, results)

    # resolve besluittypen
    _besluittypen = {besluit.besluittype for besluit in besluiten}
    with parallel() as executor:
        _resolved_besluittypen = executor.map(fetch_besluittype, _besluittypen)
    besluittypen = {bt.url: bt for bt in _resolved_besluittypen}

    # resolve all relations
    for besluit in besluiten:
        besluit.zaak = zaak
        besluit.besluittype = besluittypen[besluit.besluittype]

    return besluiten


def create_zaakbesluit(zaak: Zaak, data: Dict[str, Any]) -> Besluit:
    if not data.get("zaak"):
        data["zaak"] = zaak.url

    config = CoreConfig.get_solo()
    brc = config.primary_brc or Service.objects.filter(api_type=APITypes.brc).first()
    if not brc:
        raise RuntimeError("No BRC service configured")

    client = brc.build_client()
    besluit_data = client.create("besluit", data=data)
    return factory(Besluit, besluit_data)


def create_besluit_document(besluit: Besluit, document_url: str) -> BesluitDocument:
    client = _client_from_object(besluit)
    bio_data = client.create(
        "besluitinformatieobject",
        {
            "besluit": besluit.url,
            "informatieobject": document_url,
        },
    )
    return factory(BesluitDocument, bio_data)
