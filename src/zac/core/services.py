import asyncio
import hashlib
import logging
from concurrent import futures
from typing import Dict, List

from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist

import aiohttp
from nlx_url_rewriter.rewriter import Rewriter
from zgw.models import Eigenschap, InformatieObjectType, StatusType, Zaak
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.api_models.zaken import Status
from zgw_consumers.client import get_client_class
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from zac.utils.decorators import cache as cache_result

from .utils import get_paginated_results

logger = logging.getLogger(__name__)

AN_HOUR = 60 * 60
A_DAY = AN_HOUR * 24


def _client_from_url(url: str):
    # build the client
    Client = get_client_class()
    client = Client.from_url(url)

    base_urls = [client.base_url]
    Rewriter().backwards(base_urls)
    service = Service.objects.get(api_root=base_urls[0])

    return service.build_client()


def _client_from_object(obj):
    return _client_from_url(obj.url)


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


@cache_result("zt:statustypen:{zaaktype.url}", timeout=AN_HOUR / 2)
def get_statustypen(zaaktype: ZaakType) -> List[StatusType]:
    client = _client_from_object(zaaktype)
    _statustypen = get_paginated_results(
        client, "statustype", query_params={"zaaktype": zaaktype.url}
    )
    statustypen = factory(StatusType, _statustypen)
    return statustypen


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


def get_eigenschappen(zaak: Zaak) -> List[Eigenschap]:
    client = _client_from_object(zaak)

    eigenschappen = client.list("zaakeigenschap", zaak_uuid=zaak.id)
    for _eigenschap in eigenschappen:
        _eigenschap["zaak"] = zaak

    return [Eigenschap.from_raw(_eigenschap) for _eigenschap in eigenschappen]


@cache_result("statustype:{url}", timeout=A_DAY)
def get_statustype(url: str) -> StatusType:
    client = _client_from_url(url)
    status_type = client.retrieve("statustype", url=url)
    status_type = factory(StatusType, status_type)
    return status_type


def get_documenten(zaak: Zaak) -> List[Document]:
    logger.debug("Retrieving documents linked to zaak %r", zaak)
    rewriter = Rewriter()

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
    # figure out relevant ztcs
    informatieobjecttypen = {
        document["informatieobjecttype"] for document in documenten
    }

    _iot = list(informatieobjecttypen)
    rewriter.backwards(_iot)

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

    documenten = factory(Document, documenten)

    # resolve relations
    for document in documenten:
        document.informatieobjecttype = informatieobjecttypen[
            document.informatieobjecttype
        ]

    return documenten


@cache_result("document:{bronorganisatie}:{identificatie}", timeout=AN_HOUR / 2)
def find_document(bronorganisatie: str, identificatie: str) -> Document:
    """
    Find the document uniquely identified by bronorganisatie and identificatie.
    """
    query = {"bronorganisatie": bronorganisatie, "identificatie": identificatie}

    # not in cache -> check it in all known ZRCs
    drcs = Service.objects.filter(api_type=APITypes.drc)
    claims = {}
    for drc in drcs:
        client = drc.build_client(**claims)
        results = client.list("enkelvoudiginformatieobject", query_params=query)

        if not results:
            continue

        if len(results) > 1:
            logger.warning("Found multiple Zaken for query %r", query)

        # there's only supposed to be one unique case
        result = Document.from_raw(results[0])
        break

    if result is None:
        raise ObjectDoesNotExist(
            "Document object was not found in any known registrations"
        )

    return result


async def fetch(session: aiohttp.ClientSession, url: str):
    creds = _client_from_url(url).auth.credentials()
    async with session.get(url, headers=creds) as response:
        return await response.json()


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


def get_zaak(zaak_uuid=None, zaak_url=None, zaaktypen=None) -> Zaak:
    """
    Retrieve zaak with uuid or url
    """
    zrcs = Service.objects.filter(api_type=APITypes.zrc)
    result = None

    for zrc in zrcs:
        client = zrc.build_client()
        result = client.retrieve("zaak", url=zaak_url, uuid=zaak_uuid)

        if not result:
            continue

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
        zaken.append(get_zaak(zaak_url=url, zaaktypen=zaaktypen))

    # FIXME remove string after testing
    zaken = get_zaken(zaaktypen)[:3]
    return zaken
