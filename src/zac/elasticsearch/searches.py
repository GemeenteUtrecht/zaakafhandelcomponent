from typing import List

from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen

from .documents import ZaakDocument


def search_zaken(
    size=25, zaaktypen=None, identificatie=None, bronorganisatie=None, max_va=None
) -> List[str]:
    s = ZaakDocument.search().source(["url"])[:size]
    if zaaktypen:
        s = s.filter("terms", **{"zaaktype.keyword": zaaktypen})
    if identificatie:
        s = s.filter("term", **{"identificatie.keyword": identificatie})
    if bronorganisatie:
        s = s.filter("term", **{"bronorganisatie.keyword": bronorganisatie})
    if max_va:
        max_va_order = VertrouwelijkheidsAanduidingen.get_choice(max_va).order
        s = s.filter("range", va_order={"lte": max_va_order})

    response = s.execute()
    zaak_urls = [hit.url for hit in response]
    return zaak_urls
