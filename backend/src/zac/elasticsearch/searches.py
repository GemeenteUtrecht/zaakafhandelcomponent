import operator
from functools import reduce
from typing import List, Optional, Union
from urllib.request import Request

from django.conf import settings

from elasticsearch_dsl import Q, Search
from elasticsearch_dsl.query import (
    Bool,
    Exists,
    Match,
    MultiMatch,
    Nested,
    Query,
    QueryString,
    Regexp,
    Term,
    Terms,
)

from zac.accounts.constants import PermissionObjectTypeChoices
from zac.accounts.models import BlueprintPermission, UserAtomicPermission
from zac.camunda.constants import AssigneeTypeChoices
from zac.core.permissions import zaken_inzien

from .documents import ObjectDocument, ZaakDocument


def query_allowed_for_requester(
    request: Request,
    object_type: str = PermissionObjectTypeChoices.zaak,
    permission: str = zaken_inzien.name,
) -> Query:
    """
    construct query part to display only allowed zaken
    """
    allowed = []
    if user := request.user:
        if user.is_superuser:
            return Q("match_all")

        # atomic permissions
        object_urls = (
            UserAtomicPermission.objects.filter(
                user=user,
                atomic_permission__object_type=object_type,
                atomic_permission__permission=permission,
            )
            .actual()
            .values_list("atomic_permission__object_url", flat=True)
        )
        if object_urls.count():
            allowed.append(Terms(url=list(object_urls)))

    if getattr(request.auth, "has_all_reading_rights", False):
        return Q("match_all")

    # blueprint permissions
    for blueprint_permission in BlueprintPermission.objects.for_requester(
        request, actual=True
    ).filter(object_type=object_type, role__permissions__contains=[permission]):
        allowed.append(blueprint_permission.get_search_query())

    if not allowed:
        return Q("match_none")

    return reduce(operator.or_, allowed)


def search(
    request=None,
    size=None,
    identificatie=None,
    bronorganisatie=None,
    omschrijving=None,
    zaaktypen=None,
    behandelaar=None,
    eigenschappen=None,
    urls=None,
    only_allowed=True,
    include_closed=True,
    ordering=("-identificatie.keyword", "-startdatum", "-registratiedatum"),
    fields=None,
    object=None,
) -> List[ZaakDocument]:

    size = size or 10000
    s = ZaakDocument.search()[:size]

    if identificatie:
        s = s.query(Match(identificatie={"query": identificatie}))
    if bronorganisatie:
        s = s.filter(Term(bronorganisatie=bronorganisatie))
    if omschrijving:
        s = s.query(
            QueryString(default_field="omschrijving", query=f"*{omschrijving}*")
        )
    if zaaktypen:
        s = s.filter(Terms(zaaktype__url=zaaktypen))
    if behandelaar:
        s = s.filter(
            Nested(
                path="rollen",
                query=Bool(
                    filter=[
                        Term(rollen__betrokkene_type="medewerker"),
                        Term(rollen__omschrijving_generiek="behandelaar"),
                        Term(
                            rollen__betrokkene_identificatie__identificatie=f"{AssigneeTypeChoices.user}:{behandelaar}"
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
                    query=f"*{eigenschap_value}*",
                ),
            )
    if object:
        s = s.filter(
            Nested(
                path="zaakobjecten",
                query=Bool(filter=Term(zaakobjecten__object=object)),
            )
        )

    if not include_closed:
        s = s.filter(~Exists(field="einddatum"))

    if urls:
        s = s.filter(Terms(url=urls))

    # display only allowed zaken
    if only_allowed:
        s = s.filter(query_allowed_for_requester(request))

    if ordering:
        s = s.sort(*ordering)

    if fields:
        s = s.source(fields)

    response = s.execute()
    return response.hits


def autocomplete_zaak_search(
    identificatie: str,
    request: Optional[Request] = None,
    only_allowed: bool = True,
) -> List[ZaakDocument]:
    search = ZaakDocument.search().query(
        Regexp(
            identificatie={
                "value": f".*{identificatie}.*",
                # "case_insensitive": True,  # 7.10 feature
            }
        )
    )
    if only_allowed:
        search = search.filter(query_allowed_for_requester(request))

    response = search.execute()
    return response.hits


from time import time


def quick_search(
    search_term: str,
    request: Optional[Request] = None,
    only_allowed: bool = False,
) -> List[Union[ZaakDocument, ObjectDocument]]:
    time_then = time()
    s_zaken = Search(index=[settings.ES_INDEX_ZAKEN]).source(
        [
            "bronorganisatie",
            "identificatie",
            "omschrijving",
        ]
    )
    s_zaken = s_zaken.query(
        MultiMatch(
            query=search_term,
            fields=[
                "identificatie^2",
                "omschrijving",
            ],
        ),
    )
    s_zaken.extra(size=5)

    s_objecten = Search(index=[settings.ES_INDEX_OBJECTEN])
    s_objecten = s_objecten.query(
        MultiMatch(fields=["record_data_text.*"], query=search_term)
    )
    s_objecten = s_objecten.filter(~Exists(field="record_data.meta"))
    s_objecten.extra(size=5)

    s_documenten = Search(index=[settings.ES_INDEX_DOCUMENTEN])
    s_documenten = s_documenten.query(Match(titel={"query": search_term}))
    s_documenten.extra(size=5)
    s_documenten.source(["titel", "url", "related_zaken"])
    results = {
        "zaken": s_zaken.execute(),
        "objecten": s_objecten.execute(),
        "documenten": s_documenten.execute(),
    }
    print(f"SEARCH TOOK {time()-time_then} seconds.")
    return results

    # s_objecten = Search(index=[settings.ES_INDEX_OBJECTEN])
    # s_objecten = s_objecten.suggest(
    #     "data", search_term, completion={"field": "record.data"}
    # )
    # s_objecten = s_objecten.suggest(
    #     "geometry", search_term, completion={"field": "record.geometry"}
    # )
    # s_objecten.extra(size=5).sort(["-_score"])

    # s_documenten = Search(index=[settings.ES_INDEX_DOCUMENTEN])
    # s_documenten = s_documenten.suggest(
    #     "titel", search_term, completion={"field": "titel"}
    # )
    # s_documenten.extra(size=5).sort(["-_score"])

    # if only_allowed:
    #     allowed_zaken = query_allowed_for_requester(request)
    #     s_zaken = s_zaken.filter(allowed_zaken)
    #     s_objecten = s_objecten.filter(
    #         Nested(
    #             path="related_zaken",
    #             query=Bool(filter=Terms(related_zaken__url=allowed_zaken)),
    #         )
    #     )
    #     s_documenten = s_objecten.filter(
    #         Nested(
    #             path="related_zaken",
    #             query=Bool(filter=Terms(related_zaken__url=allowed_zaken)),
    #         )
    #     )
