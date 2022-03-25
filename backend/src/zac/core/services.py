import logging
import warnings
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urljoin, urlparse

from django.contrib.auth.models import Group
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

import requests
from furl import furl
from requests.models import Response
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.besluiten import Besluit, BesluitDocument
from zgw_consumers.api_models.catalogi import (
    BesluitType,
    Eigenschap,
    InformatieObjectType,
    ResultaatType,
    RolType,
    StatusType,
    ZaakType,
)
from zgw_consumers.api_models.constants import RolTypes
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.api_models.zaken import Resultaat, Status, ZaakEigenschap, ZaakObject
from zgw_consumers.client import ZGWClient
from zgw_consumers.concurrent import parallel
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.service import get_paginated_results

from zac.accounts.constants import PermissionObjectTypeChoices
from zac.accounts.datastructures import VA_ORDER
from zac.accounts.models import BlueprintPermission, User
from zac.contrib.brp.models import BRPConfig
from zac.elasticsearch.searches import search
from zac.utils.decorators import cache as cache_result
from zac.utils.exceptions import ServiceConfigError
from zgw.models import Zaak

from .api.data import AuditTrailData
from .api.utils import convert_eigenschap_spec_to_json_schema
from .cache import invalidate_document_cache, invalidate_zaak_cache
from .models import CoreConfig
from .rollen import Rol

logger = logging.getLogger(__name__)
perf_logger = logging.getLogger("performance")

AN_HOUR = 60 * 60
A_DAY = AN_HOUR * 24


def _client_from_url(url: str):
    service = Service.get_service(url)
    if not service:
        raise ServiceConfigError(
            _("The service for the url %(url)s is not configured in the admin")
            % {"url": url}
        )
    client = service.build_client()
    return client


def _client_from_object(obj):
    return _client_from_url(obj.url)


###################################################
#                       ZTC                       #
###################################################


@cache_result("besluittype:{url}", timeout=A_DAY)
def fetch_besluittype(url: str) -> BesluitType:
    client = _client_from_url(url)
    result = client.retrieve("besluittype", url=url)
    return factory(BesluitType, result)


def _get_from_catalogus(resource: str, catalogus: str = "", **extra_query) -> List:
    """
    Retrieve informatieobjecttype or zaaktypen from all catalogi in the configured APIs.
    """
    query_params = {"catalogus": catalogus} if catalogus else {}
    query_params.update(**extra_query)
    ztcs = Service.objects.filter(api_type=APITypes.ztc)

    if catalogus:
        clients = [_client_from_url(catalogus)]
    else:
        clients = [ztc.build_client() for ztc in ztcs]

    result = []
    for client in clients:
        result += get_paginated_results(client, resource, query_params=query_params)

    return result


@cache_result("zaaktypen:{catalogus}", timeout=AN_HOUR)
def _get_zaaktypen(catalogus: str = "") -> List[ZaakType]:
    """
    Retrieve all the zaaktypen from all catalogi in the configured APIs.
    """
    results = _get_from_catalogus(resource="zaaktype", catalogus=catalogus)
    return factory(ZaakType, results)


@cache_result("informatieobjecttypen:{catalogus}", timeout=AN_HOUR)
def get_informatieobjecttypen(catalogus: str = "") -> List[InformatieObjectType]:
    """
    Retrieve all the specified informatieobjecttypen from all catalogi in the configured APIs.
    """
    results = _get_from_catalogus(resource="informatieobjecttype", catalogus=catalogus)
    return factory(InformatieObjectType, results)


def get_zaaktypen(
    user: Optional[User] = None,
    catalogus: str = "",
    omschrijving: str = "",
) -> List[ZaakType]:
    zaaktypen = _get_zaaktypen(catalogus=catalogus)

    if omschrijving:
        zaaktypen = [
            zaaktype for zaaktype in zaaktypen if zaaktype.omschrijving == omschrijving
        ]

    if user is None or user.is_superuser:
        return zaaktypen

    # filter out zaaktypen from permissions
    zaaktypen_policies = (
        BlueprintPermission.objects.for_user(user)
        .filter(object_type=PermissionObjectTypeChoices.zaak)
        .actual()
        .values_list("policy", flat=True)
        .distinct()
    )
    zaaktypen_policies = list(zaaktypen_policies)

    return [
        zaaktype
        for zaaktype in zaaktypen
        if [
            policy
            for policy in zaaktypen_policies
            if policy["catalogus"] == zaaktype.catalogus
            and policy["zaaktype_omschrijving"] == zaaktype.omschrijving
            and VA_ORDER[policy["max_va"]]
            >= VA_ORDER[zaaktype.vertrouwelijkheidaanduiding]
        ]
    ]


@cache_result("zaaktype:{url}", timeout=A_DAY)
def fetch_zaaktype(url: str) -> ZaakType:
    client = _client_from_url(url)
    result = client.retrieve("zaaktype", url=url)
    return factory(ZaakType, result)


def get_zaaktype(url: str, user: Optional[User] = None) -> Optional[ZaakType]:
    """
    Calls fetch_zaaktype, but filters the result on the user's permissions.
    """
    zaaktype = fetch_zaaktype(url)
    if user is None or user.is_superuser:
        return zaaktype

    zaaktypen_policies = (
        BlueprintPermission.objects.for_user(user)
        .filter(object_type=PermissionObjectTypeChoices.zaak)
        .actual()
        .values_list("policy", flat=True)
        .distinct()
    )
    zaaktypen_policies = list(zaaktypen_policies)
    return (
        zaaktype
        if [
            policy
            for policy in zaaktypen_policies
            if policy["catalogus"] == zaaktype.catalogus
            and policy["zaaktype_omschrijving"] == zaaktype.omschrijving
            and VA_ORDER[policy["max_va"]]
            >= VA_ORDER[zaaktype.vertrouwelijkheidaanduiding]
        ]
        else None
    )


@cache_result("zt:statustypen:{zaaktype.url}", timeout=A_DAY)
def get_statustypen(zaaktype: ZaakType) -> List[StatusType]:
    client = _client_from_object(zaaktype)
    _statustypen = get_paginated_results(
        client, "statustype", query_params={"zaaktype": zaaktype.url}
    )
    statustypen = factory(StatusType, _statustypen)
    return statustypen


@cache_result("statustype:{url}", timeout=A_DAY)
def get_statustype(url: str) -> StatusType:
    client = _client_from_url(url)
    status_type = client.retrieve("statustype", url=url)
    status_type = factory(StatusType, status_type)
    return status_type


@cache_result("zt:resultaattypen:{zaaktype.url}", timeout=A_DAY)
def get_resultaattypen(zaaktype: ZaakType) -> List[ResultaatType]:
    client = _client_from_object(zaaktype)
    resultaattypen = get_paginated_results(
        client,
        "resultaattype",
        query_params={"zaaktype": zaaktype.url},
    )

    resultaattypen = factory(ResultaatType, resultaattypen)

    # resolve relations
    for resultaattype in resultaattypen:
        resultaattype.zaaktype = zaaktype

    return resultaattypen


@cache_result("zt:eigenschappen:{zaaktype.url}", timeout=A_DAY)
def get_eigenschappen(zaaktype: ZaakType) -> List[Eigenschap]:
    client = _client_from_object(zaaktype)
    eigenschappen = get_paginated_results(
        client,
        "eigenschap",
        query_params={"zaaktype": zaaktype.url},
    )

    eigenschappen = factory(Eigenschap, eigenschappen)

    # resolve relations
    for eigenschap in eigenschappen:
        eigenschap.zaaktype = zaaktype

    return eigenschappen


@cache_result("eigenschap:{url}", timeout=A_DAY)
def get_eigenschap(url: str) -> Eigenschap:
    client = _client_from_url(url)
    result = client.retrieve("eigenschap", url)
    return factory(Eigenschap, result)


def get_eigenschappen_for_zaaktypen(zaaktypen: List[ZaakType]) -> List[Eigenschap]:
    with parallel() as executor:
        _eigenschappen = executor.map(get_eigenschappen, zaaktypen)

    eigenschappen = sum(list(_eigenschappen), [])

    # transform values and remove duplicates
    eigenschappen_aggregated = []
    for eigenschap in eigenschappen:
        existing_eigenschappen = [
            e for e in eigenschappen_aggregated if e.naam == eigenschap.naam
        ]
        if existing_eigenschappen:
            if convert_eigenschap_spec_to_json_schema(
                eigenschap.specificatie
            ) != convert_eigenschap_spec_to_json_schema(
                existing_eigenschappen[0].specificatie
            ):
                logger.warning(
                    "Eigenschappen '%(name)s' which belong to zaaktype '%(zaaktype)s' have different specs"
                    % {
                        "name": eigenschap.naam,
                        "zaaktype": eigenschap.zaaktype.omschrijving,
                    }
                )
            continue

        eigenschappen_aggregated.append(eigenschap)

    eigenschappen_aggregated = sorted(eigenschappen_aggregated, key=lambda e: e.naam)

    return eigenschappen_aggregated


@cache_result("roltype:{url}", timeout=A_DAY)
def get_roltype(url: str) -> RolType:
    client = _client_from_url(url)
    result = client.retrieve("roltype", url)
    return factory(RolType, result)


@cache_result("zt:roltypen:{zaaktype.url}:{omschrijving_generiek}", timeout=A_DAY)
def get_roltypen(zaaktype: ZaakType, omschrijving_generiek: str = "") -> list:
    query_params = {"zaaktype": zaaktype.url}
    if omschrijving_generiek:
        query_params.update({"omschrijvingGeneriek": omschrijving_generiek})
    client = _client_from_object(zaaktype)
    roltypen = get_paginated_results(client, "roltype", query_params=query_params)

    roltypen = factory(RolType, roltypen)

    return roltypen


@cache_result("ziot:{zaaktype.url}", timeout=A_DAY)
def get_informatieobjecttypen_for_zaaktype(
    zaaktype: ZaakType,
) -> List[InformatieObjectType]:
    """
    Retrieve all informatieobjecttypen relevant for a given zaaktype.
    """
    client = _client_from_object(zaaktype)
    results = get_paginated_results(
        client, "zaakinformatieobjecttype", query_params={"zaaktype": zaaktype.url}
    )
    with parallel() as executor:
        urls = [
            iot["informatieobjecttype"]
            for iot in sorted(results, key=lambda iot: iot["volgnummer"])
        ]
        results = executor.map(get_informatieobjecttype, urls)
    return list(results)


@cache_result("informatieobjecttype:{url}", timeout=A_DAY)
def get_informatieobjecttype(url: str) -> InformatieObjectType:
    client = _client_from_url(url)
    data = client.retrieve("informatieobjecttype", url=url)
    return factory(InformatieObjectType, data)


@cache_result("zt:besluittypen:{zaaktype.url}")
def get_besluittypen_for_zaaktype(zaaktype: ZaakType) -> List[BesluitType]:
    with parallel() as executor:
        results = executor.map(fetch_besluittype, zaaktype.besluittypen)
    return list(results)


###################################################
#                       ZRC                       #
###################################################


# @cache_result(
#     "zaken:{client.base_url}:{zaaktype}:{max_va}:{identificatie}:{bronorganisatie}:{extra_query}",
#     timeout=AN_HOUR,
# )
def _find_zaken(
    client,
    zaaktype: str = "",
    identificatie: str = "",
    bronorganisatie: str = "",
    max_va: str = "",
    find_all=False,
    **extra_query,
) -> List[Dict]:
    """
    Retrieve zaken for a particular client with filter parameters.
    """
    extra_query.pop("skip_cache", None)

    query = {
        "zaaktype": zaaktype,
        "identificatie": identificatie,
        "bronorganisatie": bronorganisatie,
        "maximaleVertrouwelijkheidaanduiding": max_va,
        **extra_query,
    }
    logger.debug("Querying zaken with %r", query)
    minimum = None if find_all else 25
    _zaken = get_paginated_results(
        client,
        "zaak",
        query_params=query,
        minimum=minimum,
    )
    return _zaken


def get_zaken_all_paginated(
    client: ZGWClient,
    query_params: dict = {},
) -> Tuple[List[Zaak], dict]:
    """
    Fetch all zaken from the ZRCs in batches.
    Used to index Zaken in ES.
    Should not be used for searches with user permissions
    """
    response = client.list("zaak", query_params=query_params)
    zaken = factory(Zaak, response["results"])

    if response["next"]:
        next_url = urlparse(response["next"])
        query = parse_qs(next_url.query)
        new_page = int(query["page"][0])
        query_params["page"] = [new_page]
    else:
        query_params["page"] = None

    return zaken, query_params


def get_zaken_all(
    **query_params,
) -> List[Zaak]:
    """
    Fetch all zaken from the ZRCs.
    Used to index Zaken in ES.
    Should not be used for searches with user permissions
    """

    zaaktypen = {zt.url: zt for zt in get_zaaktypen()}

    zrcs = Service.objects.filter(api_type=APITypes.zrc)
    clients = [zrc.build_client() for zrc in zrcs]

    def _get_paginated_results(client):
        return get_paginated_results(client, "zaak", query_params=query_params)

    with parallel() as executor:
        results = executor.map(_get_paginated_results, clients)
        flattened = sum(list(results), [])

    zaken = factory(Zaak, flattened)

    # resolve zaaktype reference
    for zaak in zaken:
        zaak.zaaktype = zaaktypen[zaak.zaaktype]

    # sort results by startdatum / registratiedatum / identificatie
    zaken = sorted(
        zaken,
        key=lambda zaak: (zaak.registratiedatum, zaak.startdatum, zaak.identificatie),
        reverse=True,
    )

    return zaken


def search_zaak_for_related_object(queries: List[dict], resource) -> List[Zaak]:
    zrcs = Service.objects.filter(api_type=APITypes.zrc)
    clients = [zrc.build_client() for zrc in zrcs]

    def _get_related_objects(client) -> list:
        related_objects = []
        for query in queries:
            related_objects += get_paginated_results(
                client, resource, query_params=query
            )
        return related_objects

    def _get_zaak(args):
        client, zaak_url = args
        return get_zaak(zaak_uuid=None, zaak_url=zaak_url, client=client)

    with parallel(max_workers=10) as executor:
        results = executor.map(_get_related_objects, clients)

        job_args = []
        for client, related_objects in zip(clients, results):
            zaak_urls = set(ro["zaak"] for ro in related_objects)
            job_args += [(client, zaak_url) for zaak_url in zaak_urls]
        zaken_results = executor.map(_get_zaak, job_args)

    zaken = list(zaken_results)

    def _resolve_zaaktype(zaak):
        zaak.zaaktype = fetch_zaaktype(zaak.zaaktype)

    with parallel(max_workers=10) as executor:
        for zaak in zaken:
            executor.submit(_resolve_zaaktype, zaak)

    return zaken


def search_zaken_for_object(object_url: str) -> List[Zaak]:
    """
    Query the ZRCs for zaken that have object_url as a zaakobject.
    """
    query = {"object": object_url}
    return search_zaak_for_related_object([query], "zaakobject")


def search_zaken_for_bsn(bsn: str) -> List[Zaak]:
    brp_config = BRPConfig.get_solo()
    service = brp_config.service

    queries = [
        {"betrokkeneIdentificatie__natuurlijkPersoon__inpBsn": bsn},
    ]

    if service:
        brp_url = urljoin(service.api_root, "ingeschrevenpersonen")
        queries += [
            {"betrokkene": f"{brp_url}/{bsn}"},
            {"betrokkene": f"{brp_url}?burgerservicenummer={bsn}"},
        ]

    return search_zaak_for_related_object(queries, "rol")


# TODO: listen for notifiations to invalidate cache OR look into ETag when it's available
@cache_result("zaak:{bronorganisatie}:{identificatie}", timeout=AN_HOUR / 2)
def find_zaak(bronorganisatie: str, identificatie: str) -> Zaak:
    """
    Find the Zaak, uniquely identified by bronorganisatie & identificatie.
    """
    query = {"bronorganisatie": bronorganisatie, "identificatie": identificatie}

    # try local search index first
    results = search(size=1, only_allowed=False, **query)
    if results:
        zaak = get_zaak(zaak_url=results[0].url)
    else:
        # not in cache -> check it in all known ZRCs
        zrcs = Service.objects.filter(api_type=APITypes.zrc)
        zaak = None
        for zrc in zrcs:
            client = zrc.build_client()
            results = get_paginated_results(client, "zaak", query_params=query)

            if not results:
                continue

            if len(results) > 1:
                logger.warning("Found multiple Zaken for query %r", query)

            # there's only supposed to be one unique case
            zaak = factory(Zaak, results[0])
            break

        if zaak is None:
            raise ObjectDoesNotExist(
                "Zaak object was not found in any known registrations"
            )

    # resolve relation
    zaak.zaaktype = fetch_zaaktype(zaak.zaaktype)

    return zaak


def get_statussen(zaak: Zaak) -> List[Status]:
    client = _client_from_object(zaak)

    # re-use cached objects
    statustypen = {st.url: st for st in get_statustypen(zaak.zaaktype)}

    # fetch the statusses
    _statussen = get_paginated_results(
        client, "status", query_params={"zaak": zaak.url}
    )

    statussen = factory(Status, _statussen)

    # convert URL references into objects
    for status in statussen:
        status.statustype = statustypen[status.statustype]
        status.zaak = zaak

    return sorted(statussen, key=lambda x: x.datum_status_gezet, reverse=True)


@cache_result("zaak-status:{zaak.status}", timeout=AN_HOUR)
def get_status(zaak: Zaak) -> Optional[Status]:
    if not zaak.status:
        return None
    assert isinstance(zaak.status, str), "Status already resolved."
    client = _client_from_object(zaak)
    _status = client.retrieve("status", url=zaak.status)

    # resolve statustype
    status = factory(Status, _status)
    status.statustype = get_statustype(_status["statustype"])
    return status


def get_zaak_eigenschappen(zaak: Zaak) -> List[ZaakEigenschap]:
    # the zaak object itself already contains a list of URL references
    if not zaak.eigenschappen:
        return []

    perf_logger.info("      Fetching eigenschappen for zaak %s", zaak.identificatie)

    zrc_client = _client_from_object(zaak)
    eigenschappen = {
        eigenschap.url: eigenschap for eigenschap in get_eigenschappen(zaak.zaaktype)
    }

    zaak_eigenschappen = zrc_client.list("zaakeigenschap", zaak_uuid=zaak.uuid)

    perf_logger.info(
        "      Done fetching eigenschappen for zaak %s", zaak.identificatie
    )

    zaak_eigenschappen = factory(ZaakEigenschap, zaak_eigenschappen)

    # resolve relations
    for zaak_eigenschap in zaak_eigenschappen:
        zaak_eigenschap.eigenschap = eigenschappen[zaak_eigenschap.eigenschap]

    return zaak_eigenschappen


def fetch_zaak_eigenschap(zaak_eigenschap_url: str) -> ZaakEigenschap:
    client = _client_from_url(zaak_eigenschap_url)
    zaak_eigenschap = client.retrieve("zaakeigenschap", url=zaak_eigenschap_url)
    zaak_eigenschap = factory(ZaakEigenschap, zaak_eigenschap)
    zaak_eigenschap.eigenschap = get_eigenschap(zaak_eigenschap.eigenschap)

    return zaak_eigenschap


def create_zaak_eigenschap(
    user: Optional[User] = None, zaak_url: str = "", naam: str = "", value: str = ""
) -> Optional[ZaakEigenschap]:
    zaak = get_zaak(zaak_url=zaak_url)
    zaaktype = get_zaaktype(zaak.zaaktype, user=user)
    if not zaaktype:
        logger.info(
            "Zaaktype %s could not be retrieved for user with username '%s', aborting."
            % (zaak.zaaktype, user.username)
        )
        return None

    eigenschappen = get_eigenschappen(zaaktype)
    try:
        eigenschap_url = next(
            (eigenschap.url for eigenschap in eigenschappen if eigenschap.naam == naam)
        )
    except StopIteration:
        # eigenschap not found - abort
        logger.info("Eigenschap '%s' did not exist on the zaaktype, aborting." % naam)
        return None

    zrc_client = _client_from_url(zaak_url)
    zaak_eigenschap = zrc_client.create(
        "zaakeigenschap",
        {
            "zaak": zaak_url,
            "eigenschap": eigenschap_url,
            "waarde": value,
        },
        zaak_uuid=zaak_url.split("/")[-1],
    )
    return factory(ZaakEigenschap, zaak_eigenschap)


def update_zaak_eigenschap(zaak_eigenschap_url: str, data: dict) -> ZaakEigenschap:
    client = _client_from_url(zaak_eigenschap_url)
    zaak_eigenschap = client.partial_update(
        "zaakeigenschap", data=data, url=zaak_eigenschap_url
    )
    zaak_eigenschap = factory(ZaakEigenschap, zaak_eigenschap)
    zaak_eigenschap.eigenschap = get_eigenschap(zaak_eigenschap.eigenschap)
    return zaak_eigenschap


def delete_zaak_eigenschap(zaak_eigenschap_url: str):
    client = _client_from_url(zaak_eigenschap_url)
    client.delete("zaakeigenschap", url=zaak_eigenschap_url)


@cache_result("get_zaak:{zaak_uuid}:{zaak_url}", timeout=AN_HOUR)
def get_zaak(zaak_uuid=None, zaak_url=None, client=None) -> Zaak:
    """
    Retrieve zaak with uuid or url
    """
    if zaak_uuid and (
        zaak_uuid.startswith("http://") or zaak_uuid.startswith("https://")
    ):
        warnings.warn(
            "It looks like a URL was supplied as a zaak.uuid!",
            RuntimeWarning,
        )
        zaak_url, zaak_uuid = zaak_uuid, None

    if client is None and zaak_url is not None:
        client = _client_from_url(zaak_url)

    if client is None:
        zrcs = Service.objects.filter(api_type=APITypes.zrc)
        result = None

        for zrc in zrcs:
            client = zrc.build_client()
            result = client.retrieve("zaak", url=zaak_url, uuid=zaak_uuid)

            if not result:
                continue
    else:
        result = client.retrieve("zaak", url=zaak_url, uuid=zaak_uuid)

    result = factory(Zaak, result)

    if result is None:
        raise ObjectDoesNotExist("Zaak object was not found in any known registrations")

    return result


def get_related_zaken(zaak: Zaak) -> List[Tuple[str, Zaak]]:
    """
    return list of related zaken with selected zaaktypen
    """

    def _fetch_zaak(relevante_andere_zaak: dict) -> Tuple[str, Zaak]:
        zaak = get_zaak(zaak_url=relevante_andere_zaak["url"])
        # resolve relation(s)
        zaak.zaaktype = fetch_zaaktype(zaak.zaaktype)

        # resolve status & resultaat
        zaak.status = get_status(zaak)
        zaak.resultaat = get_resultaat(zaak)

        return relevante_andere_zaak["aard_relatie"], zaak

    with parallel() as executor:
        results = list(executor.map(_fetch_zaak, zaak.relevante_andere_zaken))

    return results


@cache_result("get_zaak_objecten:{zaak.url}", timeout=AN_HOUR)
def get_zaakobjecten(zaak: Zaak) -> List[ZaakObject]:
    client = _client_from_url(zaak.url)

    zaakobjecten = get_paginated_results(
        client,
        "zaakobject",
        query_params={"zaak": zaak.url},
    )

    return factory(ZaakObject, zaakobjecten)


def get_resultaat(zaak: Zaak) -> Optional[Resultaat]:
    if not zaak.resultaat:
        return None

    client = _client_from_object(zaak)
    resultaat = client.retrieve("resultaat", url=zaak.resultaat)

    resultaat = factory(Resultaat, resultaat)

    # resolve relations
    _resultaattypen = {rt.url: rt for rt in get_resultaattypen(zaak.zaaktype)}
    resultaat.resultaattype = _resultaattypen[resultaat.resultaattype]

    return resultaat


@cache_result("rollen:{zaak.url}", alias="request", timeout=10)
def get_rollen(zaak: Zaak) -> List[Rol]:
    perf_logger.info("      Fetching rollen for zaak %s", zaak.identificatie)
    # fetch the rollen
    client = _client_from_object(zaak)
    _rollen = get_paginated_results(client, "rol", query_params={"zaak": zaak.url})
    perf_logger.info("      Done fetching rollen for zaak %s", zaak.identificatie)

    rollen = factory(Rol, _rollen)

    return rollen


@cache_result("rol:{rol_url}", timeout=AN_HOUR)
def fetch_rol(rol_url: str) -> Rol:
    client = _client_from_url(rol_url)
    rol = client.retrieve("rol", url=rol_url)

    rol = factory(Rol, rol)
    return rol


def update_rol(rol_url: str, new_rol: Dict) -> Rol:
    # Get zrc_client from the zaak url of the rol
    zrc_client = _client_from_url(new_rol["zaak"])

    # Destroy old rol
    zrc_client.delete("rol", url=rol_url)

    # Create new rol
    rol = zrc_client.create("rol", new_rol)
    return factory(Rol, rol)


def update_medewerker_identificatie_rol(rol_url: str) -> Optional[Rol]:
    # Get latest list of rollen that belong to the zaak
    rol = fetch_rol(rol_url)

    if rol.betrokkene_type != RolTypes.medewerker or rol.betrokkene:
        return

    # if there is some name - do nothing.
    # Can't use rol.get_name() cause it can return betrokkene_identificatie["identificatie"]
    if (
        rol.betrokkene_identificatie["voorletters"]
        or rol.betrokkene_identificatie["voorvoegsel_achternaam"]
        or rol.betrokkene_identificatie["achternaam"]
    ):
        return

    from .camunda.utils import resolve_assignee

    # Try to get user data
    identificatie = rol.betrokkene_identificatie["identificatie"]
    user = resolve_assignee(identificatie)
    if isinstance(user, Group):
        return

    if not user.get_full_name():
        return

    from .api.serializers import UpdateRolSerializer

    new_rol_data = UpdateRolSerializer(instance=rol, context={"user": user}).data
    new_rol = factory(Rol, new_rol_data)
    # check if the name would be changed
    if rol.get_name() == new_rol.get_name():
        return

    return update_rol(rol_url, new_rol_data)


def get_zaak_informatieobjecten(zaak: Zaak) -> list:
    client = _client_from_object(zaak)
    zaak_informatieobjecten = client.list(
        "zaakinformatieobject", query_params={"zaak": zaak.url}
    )
    return zaak_informatieobjecten


def get_informatieobjecttypen_for_zaak(url: str) -> List[InformatieObjectType]:
    zaak = get_zaak(zaak_url=url)
    zaak.zaaktype = fetch_zaaktype(zaak.zaaktype)
    informatieobjecttypen = get_informatieobjecttypen_for_zaaktype(zaak.zaaktype)
    return informatieobjecttypen


def zet_status(zaak: Zaak, statustype: StatusType, toelichting: str = "") -> Status:
    assert len(toelichting) <= 1000, "Toelichting is > 1000 characters"

    client = _client_from_object(zaak)
    status = client.create(
        "status",
        {
            "zaak": zaak.url,
            "statustype": statustype.url,
            "datumStatusGezet": timezone.now().isoformat(),
            "statustoelichting": toelichting,
        },
    )

    status = factory(Status, status)

    # resolve relations
    status.statustype = statustype

    invalidate_zaak_cache(zaak)
    return status


def get_rollen_all(**query_params) -> List[Rol]:
    """
    Retrieve all available rollen for ES indexing
    """
    zrcs = Service.objects.filter(api_type=APITypes.zrc)

    all_rollen = []
    for zrc in zrcs:
        client = zrc.build_client()

        _rollen = get_paginated_results(client, "rol", query_params=query_params)

        all_rollen += factory(Rol, _rollen)

    return all_rollen


###################################################
#                       DRC                       #
###################################################


def cache_document(
    url: str,
    response: Response,
    timeout: Optional[float] = AN_HOUR / 2,
):
    if response.status_code == 200:
        document = factory(Document, response.json())
        document_furl = furl(url)
        versie = document_furl.args.get("versie")

        cache_key = (
            f"document:{document.bronorganisatie}:{document.identificatie}:{versie}"
        )
        if cache_key not in cache:
            cache.set(cache_key, document, timeout=timeout)

        cache_key_url = f"document:{url}"
        if cache_key_url not in cache:
            cache.set(cache_key_url, response, timeout=timeout)

        if not versie:
            cache_key_versie = f"document:{document.bronorganisatie}:{document.identificatie}:{document.versie}"
            if cache_key_versie not in cache:
                cache.set(cache_key_versie, document, timeout=AN_HOUR / 2)

            document_furl.args["versie"] = document.versie
            cache_key_version_url = f"document:{document_furl.url}"
            if cache_key_version_url not in cache:
                cache.set(cache_key_version_url, response, timeout=A_DAY)


def _fetch_document(url: str) -> Response:
    """
    Retrieve document by URL from DRC or cache.
    """
    cache_key = f"document:{url}"
    if cache_key in cache:
        return cache.get(cache_key)
    client = _client_from_url(url)
    headers = client.auth.credentials()
    response = requests.get(url, headers=headers)
    cache_document(url, response)
    return response


def fetch_documents(
    zios: list, doc_versions: Optional[Dict[str, int]] = None
) -> Tuple[List[Document], List[str]]:
    doc_versions = doc_versions or {}
    document_urls = []
    for zio in zios:
        document_furl = furl(zio)
        if zio in doc_versions:
            document_furl.args["versie"] = doc_versions[zio]
        document_urls.append(document_furl.url)
    with parallel() as executor:
        responses = executor.map(lambda url: _fetch_document(url), document_urls)
    documenten = []
    gone = []
    for response, zio in zip(responses, zios):
        if response.status_code == 200:
            documenten.append(response.json())
        else:
            logger.warning("Document with url %s can't be retrieved." % zio)
            gone.append(zio)
    return factory(Document, documenten), gone


def resolve_documenten_informatieobjecttypen(
    documents: List[Document],
) -> List[Document]:
    logger.debug("Retrieving ZTC configuration for informatieobjecttypen")
    # figure out relevant ztcs
    informatieobjecttypen = {document.informatieobjecttype for document in documents}
    _iot = list(informatieobjecttypen)
    ztcs = Service.objects.filter(api_type=APITypes.ztc)
    relevant_ztcs = []
    for ztc in ztcs:
        if any(iot.startswith(ztc.api_root) for iot in _iot):
            relevant_ztcs.append(ztc)
    all_informatieobjecttypen = []
    for ztc in relevant_ztcs:
        client = ztc.build_client()
        results = get_paginated_results(client, "informatieobjecttype")
        all_informatieobjecttypen += [
            iot for iot in results if iot["url"] in informatieobjecttypen
        ]
    informatieobjecttypen = {
        iot["url"]: factory(InformatieObjectType, iot)
        for iot in all_informatieobjecttypen
    }
    # resolve relations
    for document in documents:
        document.informatieobjecttype = informatieobjecttypen[
            document.informatieobjecttype
        ]
    return documents


def get_documenten(
    zaak: Zaak, doc_versions: Optional[Dict[str, int]] = None
) -> Tuple[List[Document], List[str]]:
    logger.debug("Retrieving documents linked to zaak %r", zaak)

    # get zaakinformatieobjecten
    zaak_informatieobjecten = get_zaak_informatieobjecten(zaak)

    # retrieve the documents themselves, in parallel
    zios = [zio["informatieobject"] for zio in zaak_informatieobjecten]
    logger.debug("Fetching %d documents", len(zaak_informatieobjecten))

    # Add version to zio_url if found in doc_versions
    found, gone = fetch_documents(zios, doc_versions)
    return found, gone


@cache_result("document:{bronorganisatie}:{identificatie}:{versie}")
def find_document(
    bronorganisatie: str, identificatie: str, versie: Optional[int] = None
) -> Document:
    """
    Find the document uniquely identified by bronorganisatie and identificatie.
    """
    # not in cache -> check it in all known DRCs
    query = {"bronorganisatie": bronorganisatie, "identificatie": identificatie}

    drcs = Service.objects.filter(api_type=APITypes.drc)

    result = None
    for drc in drcs:
        client = drc.build_client()
        results = get_paginated_results(
            client, "enkelvoudiginformatieobject", query_params=query
        )

        if not results:
            continue

        # get the latest one if no explicit version is given
        if versie is None:
            result = sorted(results, key=lambda r: r["versie"], reverse=True)[0]

        else:
            # there's only supposed to be one unique case
            # NOTE: there are known issues with DRC-CMIS returning multiple docs for
            # the same version...
            candidates = [result for result in results if result["versie"] == versie]
            if len(candidates) >= 1:
                if len(candidates) > 1:
                    logger.warning(
                        "Multiple results for version '%d' found, this is an error in the DRC "
                        "implementation!",
                        versie,
                        extra={"query": query},
                    )
                result = candidates[0]

            else:
                # The DRC only returns the latest version and so the candidates
                # will always be empty if the latest version isn't the requested version.
                # In this case try to retrieve the document by using fetch_document.
                document_furl = furl(results[0]["url"]).add({"versie": versie})
                response = _fetch_document(document_furl.url)
                response.raise_for_status()
                result = response.json()
        break

    if not result:
        raise ObjectDoesNotExist(
            "Document object was not found in any known registrations"
        )

    return factory(Document, result)


def get_document(url: str) -> Document:
    """
    Retrieve document by URL.

    """
    response = _fetch_document(url)
    response.raise_for_status()
    return factory(Document, response.json())


def download_document(document: Document) -> Tuple[Document, bytes]:
    client = _client_from_object(document)
    response = requests.get(document.inhoud, headers=client.auth.credentials())
    response.raise_for_status()
    return document, response.content


def create_document(document_data: Dict) -> Document:
    core_config = CoreConfig.get_solo()
    service = core_config.primary_drc
    if not service:
        raise RuntimeError("No DRC configured!")
    drc_client = service.build_client()
    document = drc_client.create("enkelvoudiginformatieobject", document_data)
    return factory(Document, document)


def update_document(url: str, data: dict, audit_line: str) -> Document:
    client = _client_from_url(url)

    # lock eio
    lock_result = client.operation(
        "enkelvoudiginformatieobject_lock", data={}, url=f"{url}/lock"
    )
    lock = lock_result["lock"]

    data["lock"] = lock
    response = client.partial_update(
        "enkelvoudiginformatieobject",
        data=data,
        url=url,
        request_kwargs={"headers": {"X-Audit-Toelichting": audit_line}},
    )

    document = factory(Document, response)

    # unlock
    client.request(
        f"{url}/unlock",
        "enkelvoudiginformatieobject_unlock",
        "POST",
        expected_status=204,
        json={"lock": lock},
    )
    # invalid cache
    invalidate_document_cache(document)

    # refresh new state
    document = get_document(document.url)
    return document


def relate_document_to_zaak(document_url: str, zaak_url: str) -> Dict[str, str]:
    """
    Relate a document to a case.

    """
    zrc_client = Service.get_client(zaak_url)
    response = zrc_client.create(
        "zaakinformatieobject",
        {
            "informatieobject": document_url,
            "zaak": zaak_url,
        },
    )
    return response


def fetch_document_audit_trail(document_url: str) -> List[AuditTrailData]:
    drc_client = _client_from_url(document_url)
    doc_uuid = furl(document_url).path.segments[-1]
    audit_trail = drc_client.list(
        "audittrail", enkelvoudiginformatieobject_uuid=doc_uuid
    )
    return factory(AuditTrailData, audit_trail)


###################################################
#                       BRC                       #
###################################################


def get_besluiten(zaak: Zaak) -> List[Besluit]:
    query = {"zaak": zaak.url}
    brcs = Service.objects.filter(api_type=APITypes.brc)

    results = []
    for brc in brcs:
        client = brc.build_client()
        results += get_paginated_results(client, "besluit", query_params=query)

    besluiten = factory(Besluit, results)

    # resolve besluittypen
    _besluittypen = {besluit.besluittype for besluit in besluiten}
    with parallel() as executor:
        _resolved_besluittypen = executor.map(fetch_besluittype, _besluittypen)
    besluittypen = {bt.url: bt for bt in _resolved_besluittypen}

    # resolve all relations
    for besluit in besluiten:
        besluit.zaak = zaak
        besluit.besluittype = besluittypen[besluit.besluittype]

    return besluiten


def create_zaakbesluit(zaak: Zaak, data: Dict[str, Any]) -> Besluit:
    if not data.get("zaak"):
        data["zaak"] = zaak.url

    config = CoreConfig.get_solo()
    brc = config.primary_brc or Service.objects.filter(api_type=APITypes.brc).first()
    if not brc:
        raise RuntimeError("No BRC service configured")

    client = brc.build_client()
    besluit_data = client.create("besluit", data=data)
    return factory(Besluit, besluit_data)


def create_besluit_document(besluit: Besluit, document_url: str) -> BesluitDocument:
    client = _client_from_object(besluit)
    bio_data = client.create(
        "besluitinformatieobject",
        {
            "besluit": besluit.url,
            "informatieobject": document_url,
        },
    )
    return factory(BesluitDocument, bio_data)


###################################################
#               Objecttypes                       #
###################################################


def fetch_objecttypes() -> List[dict]:
    conf = CoreConfig.get_solo()
    objecttype_service = conf.primary_objecttypes_api

    client = objecttype_service.build_client()
    objecttypes_data = client.list("objecttype")

    return objecttypes_data


def fetch_objecttype_version(uuid: str, version: int) -> dict:
    conf = CoreConfig.get_solo()
    objecttype_service = conf.primary_objecttypes_api

    client = objecttype_service.build_client()
    objecttypes_version_data = client.retrieve(
        "objectversion", **{"objecttype_uuid": uuid, "version": version}
    )

    return objecttypes_version_data


def search_objects(filters: dict) -> List[dict]:
    conf = CoreConfig.get_solo()
    object_service = conf.primary_objects_api

    client = object_service.build_client()
    results = client.operation(operation_id="object_search", data=filters)
    return results


def relate_object_to_zaak(relation_data: dict) -> dict:
    zrc_client = Service.get_client(relation_data["zaak"])
    assert zrc_client is not None, "ZRC client not found"

    response = zrc_client.create(
        "zaakobject",
        relation_data,
    )
    return response


def fetch_zaak_object(zaak_object_url: str):
    client = _client_from_url(zaak_object_url)
    zaak_object = client.retrieve("zaakobject", url=zaak_object_url)
    zaak_object = factory(ZaakObject, zaak_object)
    return zaak_object


def delete_zaak_object(zaak_object_url: str):
    client = _client_from_url(zaak_object_url)
    client.delete("zaakobject", url=zaak_object_url)
