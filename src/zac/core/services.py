import hashlib
import logging

from django.core.cache import cache

from zac.config.constants import APITypes
from zac.config.models import Service

logger = logging.getLogger(__name__)

CATALOGUS = '28487d3f-6a1b-489c-b03d-c75ac6693e72'


def get_zaaktypes() -> list:
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
        result += client.list('zaaktype', catalogus_uuid=CATALOGUS)

    cache.set(KEY, result, 60 * 60)
    return result


def get_zaken(zaaktypes=None) -> list:
    """
    Fetch all zaken from the ZRCs.
    """
    if zaaktypes is None:
        zaaktypes = [zt['url'] for zt in get_zaaktypes()]

    zt_key = ','.join(sorted(zaaktypes))
    cache_key = hashlib.md5(f"zaken.{zt_key}".encode('ascii')).hexdigest()

    zaken = cache.get(cache_key)
    if zaken is not None:
        logger.debug("Zaken cache hit")
        return zaken

    claims = {
        'scopes': ['zds.scopes.zaken.lezen'],
        'zaaktypes': zaaktypes,
    }
    zrcs = Service.objects.filter(api_type=APITypes.zrc)

    zaken = []
    for zrc in zrcs:
        client = zrc.build_client(**claims)
        zaken += client.list('zaak')['results']

    cache.set(cache_key, zaken, 60 * 30)

    return zaken
