import hashlib
import itertools

from django.core.cache import cache

from zgw.models.zrc import Zaak
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.client import Client

ALL_VAS_SORTED = list(VertrouwelijkheidsAanduidingen.values.keys())


def invalidate_zaak_cache(zaak: Zaak):
    zaak_uuids = (None, zaak.uuid)
    zaak_urls = (None, zaak.url)
    products = itertools.product(zaak_uuids, zaak_urls)
    kwargs = ["zaak_uuid", "zaak_url"]

    keys = [f"zaak:{zaak.bronorganisatie}:{zaak.identificatie}"] + [
        "get_zaak:{zaak_uuid}:{zaak_url}".format(**dict(zip(kwargs, product)))
        for product in products
    ]

    for key in keys:
        cache.delete(key)


def invalidate_zaak_list_cache(client: Client, zaak: Zaak):
    zaaktypes = ("", zaak.zaaktype)
    identificaties = ("", zaak.identificatie)
    bronorganisaties = ("", zaak.bronorganisatie)
    relevant_vas = [""] + ALL_VAS_SORTED[
        : ALL_VAS_SORTED.index(zaak.vertrouwelijkheidaanduiding) + 1
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

    for key in cache_keys:
        cache.delete(key)


def invalidate_document_cache(document: Document):
    key = f"document:{document.bronorganisatie}:{document.identificatie}"
    cache.delete(key)


def invalid_zio_cache(zaak: Zaak):
    from .services import get_zaak_informatieobjecten

    zaak_informatieobjecten = get_zaak_informatieobjecten(zaak)
    zios = [zio["informatieobject"] for zio in zaak_informatieobjecten]

    # construct cache keys
    permutations = itertools.permutations(zios)
    for permutation in permutations:
        key = "zios:{}".format(",".join(permutation))
        key = hashlib.md5(key.encode("ascii")).hexdigest()
        cache.delete(key)
