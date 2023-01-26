import operator
from functools import reduce
from typing import List, Optional, Union
from urllib.request import Request

from elasticsearch_dsl import Q, Search
from elasticsearch_dsl.query import (
    Bool,
    Exists,
    Match,
    MultiMatch,
    Nested,
    Query,
    QueryString,
    Term,
    Terms,
)
from zgw_consumers.api_models.constants import RolOmschrijving
from zgw_consumers.api_models.base import factory

from zac.accounts.constants import PermissionObjectTypeChoices
from zac.accounts.models import BlueprintPermission, UserAtomicPermission
from zac.camunda.constants import AssigneeTypeChoices
from zac.core.permissions import zaken_inzien

from .data import ParentAggregation
from .documents import InformatieObjectDocument, ObjectDocument, ZaakDocument


def query_allowed_for_requester(
    request: Request,
    object_type: str = PermissionObjectTypeChoices.zaak,
    permission: str = zaken_inzien.name,
    on_nested_field: Optional[str] = "",
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
            if on_nested_field:
                terms = {f"{on_nested_field}__url": list(object_urls)}
                allowed.append(
                    Nested(path=on_nested_field, query=Bool(filter=(Terms(**terms))))
                )
            else:
                allowed.append(Terms(url=list(object_urls)))

    if getattr(request.auth, "has_all_reading_rights", False):
        return Q("match_all")

    # blueprint permissions
    for blueprint_permission in BlueprintPermission.objects.for_requester(
        request, actual=True
    ).filter(object_type=object_type, role__permissions__contains=[permission]):
        if on_nested_field:
            allowed.append(
                Nested(
                    path=on_nested_field,
                    query=Bool(
                        must=blueprint_permission.get_search_query(
                            on_nested_field=on_nested_field
                        )
                    ),
                )
            )
        else:
            allowed.append(blueprint_permission.get_search_query())

    if not allowed:
        return Q("match_none")

    return reduce(operator.or_, allowed)


def search_zaken(
    request=None,
    size=10000,
    identificatie=None,
    identificatie_keyword=None,
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
    return_search=False,
) -> Union[List[ZaakDocument], Search]:

    s = ZaakDocument.search()

    if identificatie:
        s = s.query(Match(identificatie={"query": identificatie}))
    if identificatie_keyword:
        s = s.filter(Term(identificatie__keyword=identificatie_keyword))
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
                        Terms(
                            rollen__omschrijving_generiek=[
                                RolOmschrijving.behandelaar,
                                RolOmschrijving.initiator,
                            ]
                        ),
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

    s = s.extra(size=size)

    if return_search:
        return s

    response = s.execute()
    return response.hits


def autocomplete_zaak_search(
    identificatie: str,
    request: Optional[Request] = None,
    only_allowed: bool = True,
) -> List[ZaakDocument]:
    search = ZaakDocument.search().query(
        Match(
            identificatie={
                "query": identificatie,
            }
        )
    )
    if only_allowed:
        search = search.filter(query_allowed_for_requester(request))

    response = search.execute()
    return response.hits


def quick_search(
    search_term: str,
    only_allowed: bool = False,
    request: Optional[Request] = None,
) -> List[Union[ZaakDocument, ObjectDocument]]:
    s_zaken = (
        ZaakDocument.search()
        .source(
            [
                "bronorganisatie",
                "identificatie",
                "omschrijving",
            ]
        )
        .query(
            MultiMatch(
                query=search_term,
                fields=[
                    "identificatie^2",
                    "omschrijving",
                ],
            ),
        )
        .extra(size=15)
    )

    s_objecten = (
        ObjectDocument.search()
        .query(MultiMatch(fields=["record_data_text.*"], query=search_term))
        .filter(~Exists(field="record_data.meta"))
        .extra(size=15)
    )

    s_documenten = (
        InformatieObjectDocument.search()
        .source(["titel", "url", "related_zaken"])
        .query(Match(titel={"query": search_term}))
        .extra(size=15)
    )

    if only_allowed:
        if not request:
            raise RuntimeError("If only_allowed is True a request must be passed.")

        allowed = query_allowed_for_requester(request)
        s_zaken = s_zaken.filter(allowed)

        allowed = query_allowed_for_requester(request, on_nested_field="related_zaken")
        s_objecten = s_objecten.filter(allowed)
        s_documenten = s_documenten.filter(allowed)

    results = {
        "zaken": s_zaken.execute(),
        "objecten": s_objecten.execute(),
        "documenten": s_documenten.execute(),
    }
    return results


def count_by_zaaktype(request: Optional[Request] = None) -> List[ParentAggregation]:
    s = search_zaken(size=0, request=request, return_search=True, only_allowed=True)

    # elasticsearch-dsl does not support multiterm aggregation yet - workaround.
    s.aggs.bucket("parent", "terms", field="zaaktype.catalogus")
    s.aggs["parent"].bucket("child", "terms", field="zaaktype.identificatie")
    results = [bucket.to_dict() for bucket in s.execute().aggregations.parent.buckets]
    return factory(ParentAggregation, results)
