import operator
from functools import reduce
from typing import List

from elasticsearch_dsl import Q
from elasticsearch_dsl.query import (
    Bool,
    Exists,
    Match,
    Nested,
    QueryString,
    Range,
    Regexp,
    Term,
    Terms,
)
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen

from .documents import ZaakDocument

SUPPORTED_QUERY_PARAMS = (
    "identificatie",
    "bronorganisatie",
    "omschrijving",
    "zaaktypen",
    "behandelaar",
    "eigenschappen",
    "ordering",
)


def search(
    size=None,
    identificatie=None,
    bronorganisatie=None,
    omschrijving=None,
    zaaktypen=None,
    behandelaar=None,
    eigenschappen=None,
    allowed=(),
    include_closed=True,
    ordering=("-identificatie", "-startdatum", "-registratiedatum"),
) -> List[str]:

    size = size or 10000
    s = ZaakDocument.search()[:size]

    if identificatie:
        s = s.filter(Term(identificatie=identificatie))
    if bronorganisatie:
        s = s.filter(Term(bronorganisatie=bronorganisatie))
    if omschrijving:
        s = s.query(Match(omschrijving=omschrijving))
    if zaaktypen:
        s = s.filter(Terms(zaaktype=zaaktypen))
    if behandelaar:
        s = s.filter(
            Nested(
                path="rollen",
                query=Bool(
                    filter=[
                        Term(rollen__betrokkene_type="medewerker"),
                        Term(rollen__omschrijving_generiek="behandelaar"),
                        Term(
                            rollen__betrokkene_identificatie__identificatie=behandelaar
                        ),
                    ]
                ),
            )
        )
    if eigenschappen:
        for eigenschap_name, eigenschap_value in eigenschappen.items():
            # replace points in the field name because ES can't process them
            # see https://discuss.elastic.co/t/class-cast-exception-for-dynamic-field-with-in-its-name/158819/5
            s = s.query(
                QueryString(
                    fields=[f"eigenschappen.*.{eigenschap_name.replace('.', ' ')}"],
                    query=eigenschap_value,
                )
            )

    if not include_closed:
        s = s.filter(~Exists(field="einddatum"))

    # construct query part to display only allowed zaken
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


def autocomplete_zaak_search(identificatie: str) -> List[ZaakDocument]:
    search = ZaakDocument.search().query(
        Regexp(
            identificatie={
                "value": f".*{identificatie}.*",
                # "case_insensitive": True,  # 7.10 feature
            }
        )
    )
    response = search.execute()
    return response.hits
