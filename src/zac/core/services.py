import hashlib
import logging
from typing import Dict, List

from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist

from dateutil.parser import parse
from zds_client import Client, ClientAuth
from zgw.models import Status, StatusType, Zaak, ZaakType
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

logger = logging.getLogger(__name__)


def _get_zaaktypes() -> List[Dict]:
    """
    Read the configured zaaktypes and cache the result.
    """
    KEY = 'zaaktypes'

    result = cache.get(KEY)
    if result:
        logger.debug("Zaaktypes cache hit")
        return result

    result = []

    ztcs = Service.objects.filter(api_type=APITypes.ztc)
    for ztc in ztcs:
        client = ztc.build_client(scopes=['zds.scopes.zaaktypes.lezen'])
        catalogus_uuid = ztc.extra.get('main_catalogus_uuid')
        result += client.list('zaaktype', catalogus_uuid=catalogus_uuid)

    cache.set(KEY, result, 60 * 60)
    return result


def get_zaaktypes() -> List[ZaakType]:
    zaaktypes_raw = _get_zaaktypes()
    return [ZaakType.from_raw(raw) for raw in zaaktypes_raw]


def get_zaken(zaaktypes: List[str] = None) -> List[Zaak]:
    """
    Fetch all zaken from the ZRCs.
    """
    _zaaktypes = get_zaaktypes()

    if zaaktypes is None:
        zaaktypes = [zt.id for zt in get_zaaktypes()]

    zt_key = ','.join(sorted(zaaktypes))
    cache_key = hashlib.md5(f"zaken.{zt_key}".encode('ascii')).hexdigest()

    zaken = cache.get(cache_key)
    if zaken is not None:
        logger.debug("Zaken cache hit")
        return zaken

    claims = {
        'scopes': ['zds.scopes.zaken.lezen'],
        'zaaktypes': [zt.url for zt in _zaaktypes if zt.id in zaaktypes],
    }
    zrcs = Service.objects.filter(api_type=APITypes.zrc)

    zaken = []
    for zrc in zrcs:
        client = zrc.build_client(**claims)
        _zaken = client.list('zaak')['results']
        zaken += [Zaak.from_raw(raw) for raw in _zaken]

    cache.set(cache_key, zaken, 60 * 30)

    return zaken


def find_zaak(bronorganisatie: str, identificatie: str) -> Zaak:
    """
    Find the Zaak, uniquely identified by bronorganisatie & identificatie.
    """
    cache_key = f"zaak:{bronorganisatie}:{identificatie}"
    result = cache.get(cache_key)
    if result is not None:
        # TODO: when ETag is implemented, check that the cache is still up to
        # date!
        return result

    query = {
        'bronorganisatie': bronorganisatie,
        'identificatie': identificatie,
    }

    # not in cache -> check it in all known ZRCs
    zrcs = Service.objects.filter(api_type=APITypes.zrc)
    claims = {
        'scopes': ['zds.scopes.zaken.lezen'],
        'zaaktypes': [zt.url for zt in get_zaaktypes()],
    }
    for zrc in zrcs:
        client = zrc.build_client(**claims)
        results = client.list('zaak', query_params=query)['results']

        if not results:
            continue

        if len(results) > 1:
            logger.warning("Found multiple Zaken for query %r", query)

        # there's only supposed to be one unique case
        result = Zaak.from_raw(results[0])
        break

    if result is None:
        raise ObjectDoesNotExist("Zaak object was not found in any known registrations")

    cache.set(cache_key, result, 60 * 30)
    return result


def get_statussen(zaak: Zaak) -> List[Status]:
    claims = {
        'scopes': ['zds.scopes.zaken.lezen'],
        'zaaktypes': [zaak.zaaktype],
    }

    # build the client
    client = Client.from_url(zaak.url)
    service = Service.objects.get(api_root=client.base_url)
    client.auth = ClientAuth(client_id=service.client_id, secret=service.secret, **claims)

    # fetch the statusses
    _statussen = client.list('status', query_params={'zaak': zaak.url})
    statussen = []
    for _status in _statussen:
        # convert URL reference into object
        _status['statusType'] = get_statustype(_status['statusType'])
        _status['zaak'] = zaak
        _status['datumStatusGezet'] = parse(_status['datumStatusGezet'])
        statussen.append(Status.from_raw(_status))

    return sorted(statussen, key=lambda x: x.datum_status_gezet)


def get_statustype(url: str) -> StatusType:
    cache_key = f"statustype:{url}"
    result = cache.get(cache_key)
    if result is not None:
        # TODO: when ETag is implemented, check that the cache is still up to
        # date!
        return result

    # build client
    client = Client.from_url(url)
    service = Service.objects.get(api_root=client.base_url)
    client.auth = ClientAuth(client_id=service.client_id, secret=service.secret, **{
        'scopes': ['zds.scopes.zaaktypes.lezen']
    })

    # get statustype
    status_type = client.retrieve('statustype', url=url)

    result = StatusType.from_raw(status_type)
    cache.set(cache_key, result, 60 * 30)
    return result


def get_documenten(zaak: Zaak):
    claims = {
        'scopes': ['zds.scopes.zaken.lezen'],
        'zaaktypes': [zaak.zaaktype],
    }

    # build the client
    client = Client.from_url(zaak.url)
    service = Service.objects.get(api_root=client.base_url)
    client.auth = ClientAuth(client_id=service.client_id, secret=service.secret, **claims)

    # get zaakinformatieobjecten
    zaak_informatieobjecten = client.list('zaakinformatieobject', zaak_uuid=zaak.id)



    return zaak_informatieobjecten
