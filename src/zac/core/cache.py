import itertools

from django.core.cache import cache

from zgw.models.zrc import Zaak
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
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
