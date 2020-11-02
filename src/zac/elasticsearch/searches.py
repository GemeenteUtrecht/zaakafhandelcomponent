import operator
from functools import reduce
from typing import List

from elasticsearch_dsl import Q
from elasticsearch_dsl.query import Bool, Nested, Range, Term, Terms
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


def search(
    size=25,
    identificatie=None,
    bronorganisatie=None,
    zaaktypen=None,
    allowed=(),
    ordering=("-identificatie", "-startdatum", "-registratiedatum"),
):
    s = ZaakDocument.search()[:size]

    if identificatie:
        s = s.filter(Term(identificatie=identificatie))
    if bronorganisatie:
        s = s.filter(Term(bronorganisatie=bronorganisatie))
    if zaaktypen:
        s = s.filter(Terms(zaaktype=zaaktypen))

    _filters = []
    for filter in allowed:
        combined = Q("match_all")

        if filter["zaaktypen"]:
            combined = combined & Terms(zaaktype=filter["zaaktypen"])

        if filter["max_va"]:
            max_va_order = VertrouwelijkheidsAanduidingen.get_choice(
                filter["max_va"]
            ).order
            combined = combined & Range(va_order={"lte": max_va_order})

        if filter["oo"]:
            combined = combined & Nested(
                path="rollen",
                query=Bool(
                    filter=[
                        Term(rollen__betrokkene_type="organisatorische_eenheid"),
                        Term(
                            rollen__betrokkene_identificatie__identificatie=filter["oo"]
                        ),
                    ]
                ),
            )

        _filters.append(combined)

    if _filters:
        combined_filter = reduce(operator.or_, _filters)
        s = s.filter(combined_filter)

    if ordering:
        s = s.sort(*ordering)

    response = s.execute()
    zaak_urls = [hit.url for hit in response]
    return zaak_urls
