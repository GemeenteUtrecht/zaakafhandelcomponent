import itertools
from typing import List, Optional

from django.core.cache import cache, caches

from furl import furl
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.client import Client

from zgw.models.zrc import Zaak

ALL_VAS_SORTED = list(VertrouwelijkheidsAanduidingen.values.keys())


def invalidate_zaaktypen_cache(catalogus: str = ""):
    key = f"zaaktypen:{catalogus}"
    cache.delete(key)


def invalidate_informatieobjecttypen_cache(catalogus: str = ""):
    key = f"informatieobjecttypen:{catalogus}"
    cache.delete(key)


def invalidate_zaak_cache(zaak: Zaak):
    zaak_uuids = (None, zaak.uuid)
    zaak_urls = (None, zaak.url)
    products = itertools.product(zaak_uuids, zaak_urls)
    kwargs = ["zaak_uuid", "zaak_url"]

    keys = [f"zaak:{zaak.bronorganisatie}:{zaak.identificatie}"] + [
        "get_zaak:{zaak_uuid}:{zaak_url}".format(**dict(zip(kwargs, product)))
        for product in products
    ]

    cache.delete_many(keys)


def invalidate_zaak_list_cache(client: Client, zaak: Zaak):
    zaaktypes = ("", zaak.zaaktype)
    identificaties = ("", zaak.identificatie)
    bronorganisaties = ("", zaak.bronorganisatie)
    relevant_vas = [""] + ALL_VAS_SORTED[
        ALL_VAS_SORTED.index(zaak.vertrouwelijkheidaanduiding) :
    ]

    template = (
        "zaken:{client.base_url}:{zaaktype}:{max_va}:{identificatie}:{bronorganisatie}"
    )

    cache_keys = [
        template.format(
            client=client,
            **dict(
                zip(("zaaktype", "max_va", "identificatie", "bronorganisatie"), prod)
            ),
        )
        for prod in itertools.product(
            zaaktypes, relevant_vas, identificaties, bronorganisaties
        )
    ]

    cache.delete_many(cache_keys)


def invalidate_document_cache(document: Document):
    versioned_url = furl(document.url).set({"versie": document.versie}).url
    alfresco_zero_version_url = furl(document.url).set({"versie": 0}).url
    keys = [
        f"document:{document.bronorganisatie}:{document.identificatie}:0",
        f"document:{document.bronorganisatie}:{document.identificatie}:{document.versie}",
        f"document:{document.bronorganisatie}:{document.identificatie}:None",
        f"document:{alfresco_zero_version_url}",
        f"document:{versioned_url}",
        f"document:{document.url}",
    ]
    cache.delete_many(keys)


def invalidate_rollen_cache(zaak: Zaak, rol_urls: Optional[List[str]] = None):
    _cache = caches["request"]
    if _cache:
        _cache.delete(f"rollen:{zaak.url}")

    if rol_urls:
        cache_keys = []
        for rol_url in rol_urls:
            cache_keys.append(f"rol:{rol_url}")

        cache.delete_many(cache_keys)


def invalidate_zaakobjecten_cache(zaak: Zaak):
    key = f"get_zaak_objecten:{zaak.url}"
    cache.delete(key)
