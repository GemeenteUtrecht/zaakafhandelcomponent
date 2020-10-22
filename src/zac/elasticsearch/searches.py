from typing import List

from elasticsearch_dsl import Q
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen

from .documents import ZaakDocument


def search_zaken(
    size=25,
    zaaktypen=None,
    identificatie=None,
    bronorganisatie=None,
    max_va=None,
    oo=None,
) -> List[str]:
    s = ZaakDocument.search()[:size]
    if zaaktypen:
        s = s.filter("terms", zaaktype=zaaktypen)
    if identificatie:
        s = s.filter("term", identificatie=identificatie)
    if bronorganisatie:
        s = s.filter("term", bronorganisatie=bronorganisatie)
    if max_va:
        max_va_order = VertrouwelijkheidsAanduidingen.get_choice(max_va).order
        s = s.filter("range", va_order={"lte": max_va_order})
    if oo:
        s = s.filter(
            "nested",
            path="rollen",
            query=Q(
                "bool",
                filter=[
                    Q("term", rollen__betrokkene_type="organisatorische_eenheid"),
                    Q("term", rollen__betrokkene_identificatie__identificatie=oo),
                ],
            ),
        )

    response = s.execute()
    zaak_urls = [hit.url for hit in response]
    return zaak_urls
