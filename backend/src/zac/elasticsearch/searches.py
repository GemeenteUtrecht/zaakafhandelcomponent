import operator
from functools import reduce
from typing import List

from elasticsearch_dsl import Q
from elasticsearch_dsl.query import (
    Bool,
    Exists,
    Nested,
    Query,
    QueryString,
    Regexp,
    Term,
    Terms,
)

from zac.accounts.constants import PermissionObjectType
from zac.accounts.models import BlueprintPermission, User, UserAtomicPermission
from zac.core.permissions import zaken_inzien

from .documents import ZaakDocument

SUPPORTED_QUERY_PARAMS = (
    "identificatie",
    "bronorganisatie",
    "omschrijving",
    "zaaktypen",
    "behandelaar",
    "eigenschappen",
    "zaakobject",
    "ordering",
    "fields",
)


def query_allowed_for_user(
    user: User,
    object_type: str = PermissionObjectType.zaak,
    permission: str = zaken_inzien.name,
) -> Query:
    """
    construct query part to display only allowed zaken
    """
    if user.is_superuser:
        return Q("match_all")

    allowed = []

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

    # blueprint permissions
    for blueprint_permission in (
        BlueprintPermission.objects.for_user(user)
        .actual()
        .filter(object_type=object_type, permission=permission)
    ):
        allowed.append(blueprint_permission.get_search_query())

    if not allowed:
        return Q("match_none")

    return reduce(operator.or_, allowed)


def search(
    user=None,
    size=None,
    identificatie=None,
    bronorganisatie=None,
    omschrijving=None,
    zaaktypen=None,
    behandelaar=None,
    eigenschappen=None,
    only_allowed=True,
    include_closed=True,
    ordering=("-identificatie", "-startdatum", "-registratiedatum"),
    fields=None,
    zaakobject=None,
) -> List[ZaakDocument]:

    size = size or 10000
    s = ZaakDocument.search()[:size]

    if identificatie:
        s = s.filter(Term(identificatie=identificatie))
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
    if zaakobject:
        s = s.filter(
            Nested(path="objecten", query=Bool(filter=Term(objecten__url=zaakobject)))
        )

    if not include_closed:
        s = s.filter(~Exists(field="einddatum"))

    # display only allowed zaken
    if only_allowed:
        s = s.filter(query_allowed_for_user(user))

    if ordering:
        s = s.sort(*ordering)

    if fields:
        s = s.source(fields)

    response = s.execute()
    return response.hits


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
