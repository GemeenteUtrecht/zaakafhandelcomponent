import operator
from collections import defaultdict
from datetime import datetime
from functools import reduce
from typing import Any, Dict, List, Optional, Union
from urllib.request import Request

from django.conf import settings

from elasticsearch_dsl import Q, Search
from elasticsearch_dsl.query import (
    Bool,
    Exists,
    Match,
    MatchNone,
    MultiMatch,
    Nested,
    Query,
    QueryString,
    Term,
    Terms,
)
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.constants import RolOmschrijving

from zac.accounts.constants import PermissionObjectTypeChoices
from zac.accounts.models import BlueprintPermission, UserAtomicPermission
from zac.camunda.constants import AssigneeTypeChoices
from zac.core.models import MetaObjectTypesConfig
from zac.core.permissions import zaken_inzien

from .data import ParentAggregation
from .documents import (
    InformatieObjectDocument,
    ObjectDocument,
    ZaakDocument,
    ZaakInformatieObjectDocument,
    ZaakObjectDocument,
)


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


def search_zaakobjecten(
    zaken: Optional[List[str]] = None,
    objecten: Optional[List[str]] = None,
    urls: Optional[List[str]] = None,
    size: int = settings.ES_SIZE,
) -> List[ZaakObjectDocument]:
    s = ZaakObjectDocument.search()

    if not zaken and not objecten and not urls:
        return list()

    if objecten:
        s = s.filter(Terms(object=objecten))
    if zaken:
        s = s.filter(Terms(zaak=zaken))
    if urls:
        s = s.filter(Terms(url=urls))

    s = s.extra(size=size)
    results = s.execute()
    return results.hits


def search_zaken(
    request=None,
    size=settings.ES_SIZE,
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
    obj=None,
    start_period=None,
    end_period=None,
    return_search=False,
) -> Union[List[ZaakDocument], Search]:
    s = ZaakDocument.search()
    range_kwargs = {}
    if start_period:
        range_kwargs["gte"] = start_period.strftime("%Y-%m-%dT%H:%M:%S")
    if end_period:
        range_kwargs["lte"] = end_period.strftime("%Y-%m-%dT%H:%M:%S")
    if range_kwargs:
        s = s.filter("range", **{"registratiedatum": range_kwargs})
    if identificatie:
        s = s.query(Match(identificatie={"query": identificatie}))
    if identificatie_keyword:
        s = s.filter(Term(identificatie__keyword=identificatie_keyword))
    if bronorganisatie:
        s = s.filter(Term(bronorganisatie=bronorganisatie))
    if omschrijving:
        s = s.query(Match(omschrijving=omschrijving))
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
    if obj:
        zon = search_zaakobjecten(zaken=urls, objecten=[obj])
        zaakobject_zaakurls = [zo.zaak for zo in zon]
        if urls:
            urls += zaakobject_zaakurls
        else:
            urls = zaakobject_zaakurls
    if urls:
        s = s.filter(Terms(url=list(set(urls))))
    elif type(urls) == list:  # apparently we've gotten an empty list -> show nothing.
        s = s.filter(MatchNone())
    if not include_closed:
        s = s.filter(~Exists(field="einddatum"))
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
    search = search.extra(size=settings.ES_SIZE)
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
    meta_config = MetaObjectTypesConfig.get_solo()
    urls = [url for url in meta_config.meta_objecttype_urls.values() if url]
    s_objecten = (
        ObjectDocument.search()
        .query(MultiMatch(fields=["record_data_text.*"], query=search_term))
        .filter(~Terms(type__url=urls))
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


def count_by_behandelaar(request: Request) -> int:
    s = search_zaken(
        size=0,
        request=request,
        behandelaar=request.user.username,
        return_search=True,
        only_allowed=True,
    )
    return s.count()


def search_informatieobjects(
    size: int = settings.ES_SIZE,
    zaak: str = "",
    bestandsnaam: str = "",
    bronorganisatie: str = "",
    identificatie: str = "",
    iots_omschrijvingen: Optional[List[str]] = None,
    urls: Optional[List[str]] = None,
    ordering: List = [
        "titel.keyword",
    ],
    fields: Optional[List[str]] = None,
    return_search: bool = False,
    start_period=None,
    end_period=None,
) -> List[InformatieObjectDocument]:
    s = InformatieObjectDocument.search()

    if zaak:
        s = s.filter(
            Nested(
                path="related_zaken",
                query=Bool(filter=Term(related_zaken__url=zaak)),
            )
        )
    if bestandsnaam:
        s = s.filter(Term(bestandsnaam=bestandsnaam))
    if bronorganisatie:
        s = s.filter(Term(bronorganisatie=bronorganisatie))
    if identificatie:
        s = s.filter(Term(identificatie=identificatie))
    if iots_omschrijvingen:
        s = s.filter(
            Terms(informatieobjecttype__omschrijving__keyword=iots_omschrijvingen)
        )
    if urls:
        s = s.filter(Terms(url=urls))
    if ordering:
        s = s.sort(*ordering)
    if fields:
        s = s.source(fields)
    range_kwargs = {}
    if start_period:
        range_kwargs["gte"] = start_period.strftime("%Y-%m-%dT%H:%M:%S")
    if end_period:
        range_kwargs["lte"] = end_period.strftime("%Y-%m-%dT%H:%M:%S")
    if range_kwargs:
        s = s.filter("range", **{"creatiedatum": range_kwargs})

    s = s.extra(size=size)
    if return_search:
        return s
    response = s.execute()
    return response.hits


def search_objects(
    size: int = settings.ES_SIZE,
    urls: Optional[List[str]] = None,
    fields: Optional[List[str]] = None,
    return_search: bool = False,
    exclude_meta: bool = True,
) -> List[InformatieObjectDocument]:
    s = ObjectDocument.search()

    if urls:
        s = s.filter(Terms(url=urls))

    if exclude_meta:
        meta_config = MetaObjectTypesConfig.get_solo()
        meta_ots = [url for url in meta_config.meta_objecttype_urls.values() if url]
        s = s.filter(~Terms(type__url=meta_ots))

    if fields:
        s = s.source(fields)

    s = s.extra(size=size)
    if return_search:
        return s

    response = s.execute()
    return response.hits


def count_by_iot_in_zaak(zaak: str) -> Dict[str, int]:
    s = search_informatieobjects(zaak=zaak, size=0, return_search=True)

    # elasticsearch-dsl does not support multiterm aggregation yet - workaround.
    s.aggs.bucket("parent", "terms", field="informatieobjecttype.catalogus")
    s.aggs["parent"].bucket(
        "child", "terms", field="informatieobjecttype.omschrijving.keyword"
    )
    results = [bucket.to_dict() for bucket in s.execute().aggregations.parent.buckets]
    results = factory(ParentAggregation, results)
    iots_found = {}
    if results and results[0].doc_count > 0:  # only one catalogus per zaak
        for bucket in results[0].child.buckets:
            iots_found[bucket.key] = bucket.doc_count
    return iots_found


def count_zio_per_given_zaken(zaken: List[str]) -> dict:
    """
    Returns a dictionary mapping each given zaak to the count of ZaakInformatieObjectDocuments.
    """
    s = ZaakInformatieObjectDocument.search()
    s = s.filter(Terms(zaak=zaken))
    s.aggs.bucket("parent", "terms", field="zaak", size=len(zaken))
    response = s.execute()
    counts = {
        bucket.key: bucket.doc_count for bucket in response.aggregations.parent.buckets
    }
    # Ensure all input zaken are present in the result, even if count is 0
    for zaak in zaken:
        counts.setdefault(zaak, 0)
    return counts


def usage_report_zaken(
    start_period: datetime,
    end_period: datetime,
) -> List[Dict[str, Any]]:
    """
    Build a usage report for zaken in a period.

    Returns a list of dicts with fields:
      - identificatie: str
      - zaaktype_omschrijving: str
      - omschrijving: str
      - registratiedatum: datetime | str | None (as provided by ES)
      - initiator_rol: str (identifier if present, else "")
      - objecten: List[{"object": <string_representation>, "objecttype": <object.type.name>}]
      - zios_count: int
    """

    # 1) Fetch zaken within the specified period, with inner_hits for initiator role
    s_zaken = search_zaken(
        only_allowed=False,
        start_period=start_period,
        end_period=end_period,
        fields=[
            "identificatie",
            "zaaktype.omschrijving",
            "omschrijving",
            "registratiedatum",
            "rollen",
            "url",
        ],
        return_search=True,
    ).filter(
        Nested(
            path="rollen",
            query=Bool(
                filter=[Term(rollen__omschrijving_generiek=RolOmschrijving.initiator)]
            ),
            inner_hits={
                "name": "initiator_rol",
                "size": 1,
            },
        )
    )

    zaken_map: Dict[str, Dict[str, Any]] = {}
    es_hits = s_zaken.execute().hits
    for hit in es_hits:
        # Extract the initiator role identificatie from inner hits (defensive)
        initiator_ident = ""
        ih = getattr(getattr(hit.meta, "inner_hits", None), "initiator_rol", None)
        if ih and getattr(ih, "hits", None):
            ident_obj = getattr(ih.hits[0], "betrokkene_identificatie", None)
            if ident_obj is not None:
                initiator_ident = getattr(ident_obj, "identificatie", "") or ""

        zaken_map[hit.url] = {
            "identificatie": hit.identificatie,
            "zaaktype_omschrijving": hit.zaaktype.omschrijving
            if getattr(hit, "zaaktype", None)
            else "",
            "omschrijving": hit.omschrijving or "",
            "registratiedatum": getattr(hit, "registratiedatum", None),
            "initiator_rol": initiator_ident,
            # to be filled below
            "objecten": [],
            "zios_count": 0,
        }

    if not zaken_map:
        return []

    zaak_urls: List[str] = list(zaken_map.keys())

    # 2) Fetch ZIO counts for these zaken
    zios_counts: Dict[str, int] = count_zio_per_given_zaken(zaken=zaak_urls)

    # 3) Fetch zaakobjecten for these zaken
    zon = search_zaakobjecten(zaken=zaak_urls)

    # 4) Collect unique object URLs and fetch objects (excluding meta), only needed fields
    object_urls = {zo.object for zo in zon}
    objects = search_objects(
        urls=list(object_urls),
        fields=["url", "string_representation", "type.name"],
        exclude_meta=True,
        return_search=False,
    )
    # Index by URL for O(1) lookup
    objects_by_url: Dict[str, Any] = {obj.url: obj for obj in objects}

    # 5) Build zaak -> list of {"object": <string_representation>, "objecttype": <type.name>}
    zaak_to_objects: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    obj_default_string = "Geen objectnaam gevonden"
    object_type_default_string = "Geen objecttypenaam gevonden"
    for zo in zon:
        obj = objects_by_url.get(zo.object)
        if not obj:
            continue
        string_repr = (
            getattr(obj, "string_representation", obj_default_string)
            or obj_default_string
        )
        # obj.type is an InnerDoc; be defensive:
        objtype_name = ""
        obj_type = getattr(obj, "type", None)
        if obj_type is not None:
            objtype_name = (
                getattr(obj_type, "name", object_type_default_string)
                or object_type_default_string
            )
        zaak_to_objects[zo.zaak].append(
            {"object": string_repr, "objecttype": objtype_name}
        )

    # 6) Attach object lists and counts to zaken
    for zurl, row in zaken_map.items():
        row["objecten"] = zaak_to_objects.get(zurl, [])
        row["zios_count"] = int(zios_counts.get(zurl, 0) or 0)

    # 7) Optional: make output deterministic — sort by registratiedatum (oldest first, None last)
    def _parse_sort_dt(val: Any) -> Optional[datetime]:
        if isinstance(val, datetime):
            return val
        if isinstance(val, str) and val:
            try:
                return datetime.fromisoformat(val.replace("Z", "+00:00"))
            except Exception:
                return None
        return None

    rows: List[Dict[str, Any]] = list(zaken_map.values())
    rows.sort(
        key=lambda r: (
            (_parse_sort_dt(r.get("registratiedatum")) is None),
            _parse_sort_dt(r.get("registratiedatum")) or datetime.max,
        )
    )

    return rows


def usage_report_informatieobjecten(
    start_period: datetime, end_period: datetime
) -> List[Dict[str, Any]]:
    """
    Return a list of dicts for InformatieObjectDocuments within [start_period, end_period],
    mapping:
      auteur                           -> "auteur"
      beschrijving                     -> "beschrijving"
      bestandsnaam                     -> "bestandsnaam"
      informatieobjecttype.omschrijving-> "informatieobjecttype"
      creatiedatum                     -> "creatiedatum"
      related_zaken.(identificatie + zaaktype.omschrijving)
                                       -> "gerelateerde zaken" (list of "<identificatie>: <zaaktype>")
    """
    gte = start_period.strftime("%Y-%m-%dT%H:%M:%S")
    lte = end_period.strftime("%Y-%m-%dT%H:%M:%S")

    source_fields = [
        "auteur",
        "beschrijving",
        "bestandsnaam",
        "informatieobjecttype.omschrijving",
        "creatiedatum",
        "related_zaken.identificatie",
        "related_zaken.zaaktype.omschrijving",
    ]

    s = (
        InformatieObjectDocument.search()
        .source(source_fields)
        .filter("range", **{"creatiedatum": {"gte": gte, "lte": lte}})
        .params(size=settings.ES_SIZE)
    )

    results: List[Dict[str, Any]] = []
    for doc in s.scan():
        auteur = getattr(doc, "auteur", "") or ""
        bestandsnaam = getattr(doc, "bestandsnaam", "") or ""
        beschrijving = getattr(doc, "beschrijving", "") or ""
        creatiedatum = getattr(doc, "creatiedatum", None)

        iot = getattr(doc, "informatieobjecttype", None)
        iot_omschrijving = getattr(iot, "omschrijving", "") if iot else ""

        related = getattr(doc, "related_zaken", []) or []
        gerelateerde_zaken_list: List[str] = []

        for rz in related:
            ident = (getattr(rz, "identificatie", None) or "").strip()
            zt = getattr(rz, "zaaktype", None)
            zt_oms = (getattr(zt, "omschrijving", None) or "").strip() if zt else ""

            # Skip completely empty pairs
            if not ident and not zt_oms:
                continue

            gerelateerde_zaken_list.append(f"{ident}: {zt_oms}".strip(": ").strip())

        results.append(
            {
                "auteur": auteur,
                "beschrijving": beschrijving,
                "bestandsnaam": bestandsnaam,
                "informatieobjecttype": iot_omschrijving,
                "creatiedatum": creatiedatum,
                "gerelateerde_zaken": gerelateerde_zaken_list,
            }
        )

    return results
