import asyncio
import hashlib
import logging
from concurrent import futures
from typing import Dict, List, Tuple, Union

from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist

import aiohttp
import requests
from zgw.models import InformatieObjectType, StatusType, Zaak
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import Eigenschap, ResultaatType, ZaakType
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.api_models.zaken import Status, ZaakEigenschap, ZaakObject
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from zac.utils.decorators import cache as cache_result

from .utils import get_paginated_results

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


@cache_result("zaaktypen", timeout=AN_HOUR)
def _get_zaaktypen() -> List[Dict]:
    """
    Retrieve all the zaaktypen from all catalogi in the configured APIs.
    """
    result = []

    ztcs = Service.objects.filter(api_type=APITypes.ztc)
    for ztc in ztcs:
        client = ztc.build_client()
        result += get_paginated_results(client, "zaaktype")

    return result


def get_zaaktypen() -> List[ZaakType]:
    zaaktypes_raw = _get_zaaktypen()
    zaaktypes = factory(ZaakType, zaaktypes_raw)
    return zaaktypes


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
        client, "resultaattype", query_params={"zaaktype": zaaktype.url},
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
        client, "eigenschap", query_params={"zaaktype": zaaktype.url},
    )

    eigenschappen = factory(Eigenschap, eigenschappen)

    # resolve relations
    for eigenschap in eigenschappen:
        eigenschap.zaaktype = zaaktype

    return eigenschappen


###################################################
#                       ZRC                       #
###################################################


@cache_result("zaken:{client.base_url}:{zaaktype}:{identificatie}:{bronorganisatie}")
def _find_zaken(
    client, zaaktype: str = "", identificatie: str = "", bronorganisatie: str = ""
) -> List[Dict]:
    """
    Retrieve zaken for a particular client with filter parameters.
    """
    query = {
        "zaaktype": zaaktype,
        "identificatie": identificatie,
        "bronorganisatie": bronorganisatie,
    }
    _zaken = get_paginated_results(client, "zaak", query_params=query, min_num=25)
    return _zaken


def get_zaken(
    zaaktypen: List[str] = None, identificatie: str = "", bronorganisatie: str = "",
) -> List[Zaak]:
    """
    Fetch all zaken from the ZRCs.
    """
    _zaaktypen = get_zaaktypen()
    zrcs = Service.objects.filter(api_type=APITypes.zrc)

    zaken = []

    job_args = []
    for zrc in zrcs:
        client = zrc.build_client()
        job_args.append(
            {
                "client": client,
                "identificatie": identificatie,
                "bronorganisatie": bronorganisatie,
                "zaaktype": "",
            }
        )

    # expand job args with zaaktype filters if needed, parallelizes as much as possible
    if zaaktypen:
        _job_args = []
        for job_arg in job_args:
            for zaaktype_url in zaaktypen:
                _job_args.append({"zaaktype": zaaktype_url, **job_arg})
        job_args = _job_args

    def _job(kwargs_dict):
        return _find_zaken(**kwargs_dict)

    with futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(_job, job_args)
        flattened = sum(list(results), [])

    zaken = factory(Zaak, flattened)

    # resolve zaaktype reference
    _zaaktypen = {zt.url: zt for zt in get_zaaktypen()}

    for zaak in zaken:
        if zaak.zaaktype not in _zaaktypen:
            zaaktype = fetch_zaaktype(zaak.zaaktype)
            _zaaktypen[zaak.zaaktype] = zaaktype

        zaak.zaaktype = _zaaktypen[zaak.zaaktype]

    # sort results by startdatum / registratiedatum / identificatie

    zaken = sorted(
        zaken,
        key=lambda zaak: (zaak.registratiedatum, zaak.startdatum, zaak.identificatie),
        reverse=True,
    )

    return zaken


def search_zaken_for_object(object_url: str) -> List[Zaak]:
    """
    Query the ZRCs for zaken that have object_url as a zaakobject.
    """
    query = {"object": object_url}
    zrcs = Service.objects.filter(api_type=APITypes.zrc)
    clients = [zrc.build_client() for zrc in zrcs]

    def _get_zaakobjecten(client):
        return get_paginated_results(client, "zaakobject", query_params=query)

    def _get_zaak(args):
        client, zaak_url = args
        return get_zaak(zaak_uuid=None, zaak_url=zaak_url, client=client)

    with futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(_get_zaakobjecten, clients)

        job_args = []
        for client, zaakobjecten in zip(clients, results):
            job_args += [(client, zo["zaak"]) for zo in zaakobjecten]
        zaken_results = executor.map(_get_zaak, job_args)

    zaken = list(zaken_results)

    def _resolve_zaaktype(zaak):
        zaak.zaaktype = fetch_zaaktype(zaak.zaaktype)

    with futures.ThreadPoolExecutor(max_workers=10) as executor:
        for zaak in zaken:
            executor.submit(_resolve_zaaktype, zaak)

    return zaken


# TODO: listen for notifiations to invalidate cache OR look into ETag when it's available
@cache_result("zaak:{bronorganisatie}:{identificatie}", timeout=AN_HOUR / 2)
def find_zaak(bronorganisatie: str, identificatie: str) -> Zaak:
    """
    Find the Zaak, uniquely identified by bronorganisatie & identificatie.
    """
    query = {"bronorganisatie": bronorganisatie, "identificatie": identificatie}

    # not in cache -> check it in all known ZRCs
    zrcs = Service.objects.filter(api_type=APITypes.zrc)
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
        raise ObjectDoesNotExist("Zaak object was not found in any known registrations")

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

    # import bpdb; bpdb.set_trace()

    # resolve relations
    for zaak_eigenschap in zaak_eigenschappen:
        zaak_eigenschap.zaak = zaak
        zaak_eigenschap.eigenschap = eigenschappen[zaak_eigenschap.eigenschap]

    return zaak_eigenschappen


@cache_result("get_zaak:{zaak_uuid}:{zaak_url}")
def get_zaak(zaak_uuid=None, zaak_url=None, client=None) -> Zaak:
    """
    Retrieve zaak with uuid or url
    """
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


def get_related_zaken(zaak: Zaak, zaaktypen) -> list:
    """
    return list of related zaken with selected zaaktypen
    """

    related_urls = [related["url"] for related in zaak.relevante_andere_zaken]

    zaken = []
    for url in related_urls:
        zaken.append(get_zaak(zaak_url=url))

    # FIXME remove string after testing
    zaken = get_zaken(zaaktypen)[:3]
    return zaken


def get_zaakobjecten(zaak: Union[Zaak, str]) -> List[ZaakObject]:
    if isinstance(zaak, Zaak):
        zaak_url = zaak.url
    else:
        zaak_url = zaak

    client = _client_from_url(zaak_url)

    zaakobjecten = get_paginated_results(
        client, "zaakobject", query_params={"zaak": zaak_url},
    )

    return factory(ZaakObject, zaakobjecten)


###################################################
#                       DRC                       #
###################################################


def get_documenten(zaak: Zaak) -> Tuple[List[Document], List[str]]:
    logger.debug("Retrieving documents linked to zaak %r", zaak)

    zrc_client = _client_from_object(zaak)

    # get zaakinformatieobjecten
    zaak_informatieobjecten = zrc_client.list(
        "zaakinformatieobject", query_params={"zaak": zaak.url}
    )

    # retrieve the documents themselves, in parallel
    cache_key = "zios:{}".format(
        ",".join([zio["informatieobject"] for zio in zaak_informatieobjecten])
    )
    cache_key = hashlib.md5(cache_key.encode("ascii")).hexdigest()

    logger.debug("Fetching %d documents", len(zaak_informatieobjecten))
    documenten = fetch_async(cache_key, fetch_documents, zaak_informatieobjecten)

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


@cache_result("document:{bronorganisatie}:{identificatie}", timeout=AN_HOUR / 2)
def find_document(bronorganisatie: str, identificatie: str) -> Document:
    """
    Find the document uniquely identified by bronorganisatie and identificatie.
    """
    query = {"bronorganisatie": bronorganisatie, "identificatie": identificatie}

    # not in cache -> check it in all known ZRCs
    drcs = Service.objects.filter(api_type=APITypes.drc)
    for drc in drcs:
        client = drc.build_client()
        results = client.list("enkelvoudiginformatieobject", query_params=query)

        if not results:
            continue

        if len(results) > 1:
            logger.warning("Found multiple Zaken for query %r", query)

        # there's only supposed to be one unique case
        result = factory(Document, results[0])
        break

    if result is None:
        raise ObjectDoesNotExist(
            "Document object was not found in any known registrations"
        )

    return result


def download_document(
    bronorganisatie: str, identificatie: str
) -> Tuple[Document, bytes]:
    document = find_document(bronorganisatie, identificatie)
    client = _client_from_object(document)
    response = requests.get(document.inhoud, headers=client.auth.credentials())
    response.raise_for_status()
    return document, response.content


async def fetch_documents(zios: list):
    tasks = []
    async with aiohttp.ClientSession() as session:
        for zio in zios:
            task = asyncio.ensure_future(
                fetch(session=session, url=zio["informatieobject"])
            )
            tasks.append(task)

        responses = await asyncio.gather(*tasks)

    return responses
