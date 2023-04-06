import itertools
from typing import List, Optional

from django.core.cache import cache, caches

from furl import furl
from requests.models import Response
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.client import Client

from zgw.models.zrc import Zaak

ALL_VAS_SORTED = list(VertrouwelijkheidsAanduidingen.values.keys())
AN_HOUR = 60 * 60


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
    if isinstance(zaak.zaaktype, ZaakType):
        zaaktypes = ("", zaak.zaaktype.url)
    elif isinstance(zaak.zaaktype, dict):
        zaaktypes = ("", zaak.zaaktype["url"])
    else:
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


def invalidate_document_url_cache(document_url: str):
    key = f"document:{document_url}"
    cache.delete(key)


def invalidate_document_other_cache(document: Document):
    alfresco_zero_version_url = furl(document.url).set({"versie": 0}).url
    keys = [
        f"document:{document.bronorganisatie}:{document.identificatie}:None",
        f"document:{alfresco_zero_version_url}",
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
    key = f"zaak_objecten:{zaak.url}"
    cache.delete(key)


def invalidate_fetch_object_cache(object_url: str):
    key = f"object:{object_url}"
    cache.delete(key)


def cache_document(
    url: str,
    response: Response,
    timeout: Optional[float] = AN_HOUR,
):
    if response.status_code == 200:
        document = factory(Document, response.json())
        document_furl = furl(url)
        versie = document_furl.args.get("versie")

        cache_key = (
            f"document:{document.bronorganisatie}:{document.identificatie}:{versie}"
        )
        if cache_key not in cache:
            cache.set(cache_key, document, timeout=timeout)

        cache_key_url = f"document:{url}"
        if cache_key_url not in cache:
            cache.set(cache_key_url, response, timeout=timeout)

        if not versie:
            cache_key_versie = f"document:{document.bronorganisatie}:{document.identificatie}:{document.versie}"
            if cache_key_versie not in cache:
                cache.set(cache_key_versie, document, timeout=timeout)

            document_furl.args["versie"] = document.versie
            cache_key_version_url = f"document:{document_furl.url}"
            if cache_key_version_url not in cache:
                cache.set(cache_key_version_url, response, timeout=timeout)


def invalidate_document_url_cache(url: str):
    document_furl = furl(url)

    # get rid of version on url if it's there
    # because the older versions are static
    # and don't need to be invalidated
    if document_furl.args.get("versie"):
        del document_furl.args["versie"]
        url = document_furl.url

    key = f"document:{url}"
    cache.delete(key)
