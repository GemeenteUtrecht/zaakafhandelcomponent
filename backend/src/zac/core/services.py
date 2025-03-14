import logging
import warnings
from functools import wraps
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin
from urllib.request import Request

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

import requests
from furl import furl
from requests.models import Response
from zds_client import ClientError
from zds_client.schema import get_operation_url
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.besluiten import Besluit, BesluitDocument
from zgw_consumers.api_models.catalogi import (
    BesluitType,
    Catalogus,
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
from zac.client import Client
from zac.contrib.brp.models import BRPConfig
from zac.contrib.objects.oudbehandelaren.cache import (
    invalidate_cache_fetch_oudbehandelaren,
)
from zac.elasticsearch.searches import search_informatieobjects, search_zaken
from zac.utils.decorators import cache as cache_result
from zac.utils.exceptions import ServiceConfigError
from zgw.models import Zaak
from zgw.models.zrc import ZaakInformatieObject

from .api.data import AuditTrailData
from .api.utils import convert_eigenschap_spec_to_json_schema
from .cache import (
    cache_document,
    invalidate_document_other_cache,
    invalidate_document_url_cache,
    invalidate_zaak_cache,
)
from .models import CoreConfig
from .rollen import Rol
from .utils import A_DAY, AN_HOUR, fetch_next_url_pagination

logger = logging.getLogger(__name__)
perf_logger = logging.getLogger("performance")


def client_from_url(url: str):
    service = Service.get_service(url)
    if not service:
        raise ServiceConfigError(
            _("The service for the url %(url)s is not configured in the admin.")
            % {"url": url}
        )
    client = service.build_client()
    return client


def _client_from_object(obj):
    return client_from_url(obj.url)


###################################################
#                       ZTC                       #
###################################################


@cache_result("besluittype:{url}", timeout=A_DAY)
def fetch_besluittype(url: str) -> BesluitType:
    client = client_from_url(url)
    result = client.retrieve("besluittype", url=url)
    return factory(BesluitType, result)


@cache_result("catalogus:{url}", timeout=A_DAY)
def fetch_catalogus(url: str) -> Catalogus:
    client = client_from_url(url)
    result = client.retrieve("catalogus", url=url)
    return factory(Catalogus, result)


def _get_from_catalogus(resource: str, catalogus: str = "", **extra_query) -> List:
    """
    Retrieve informatieobjecttype or zaaktypen from all catalogi in the configured APIs.
    """
    query_params = {"catalogus": catalogus} if catalogus else {}
    query_params.update(**extra_query)
    ztcs = Service.objects.filter(api_type=APITypes.ztc)

    if catalogus:
        clients = [client_from_url(catalogus)]
    else:
        clients = [ztc.build_client() for ztc in ztcs]

    result = []
    for client in clients:
        result += get_paginated_results(
            client, resource, request_kwargs={"params": query_params}
        )

    return result


@cache_result("zaaktypen:{catalogus}", timeout=A_DAY)
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
    request: Optional[Request] = None,
    catalogus: str = "",
    omschrijving: str = "",
    identificatie: str = "",
) -> List[ZaakType]:
    zaaktypen = _get_zaaktypen(catalogus=catalogus)
    if omschrijving:
        zaaktypen = [
            zaaktype for zaaktype in zaaktypen if zaaktype.omschrijving == omschrijving
        ]

    if identificatie:
        zaaktypen = [
            zaaktype
            for zaaktype in zaaktypen
            if zaaktype.identificatie == identificatie
        ]

    if (
        (not request)
        or (getattr(request.auth, "has_all_reading_rights", False))
        or (getattr(request.user, "is_superuser", False))
    ):
        return zaaktypen

    # filter out zaaktypen from permissions
    zaaktypen_policies = (
        BlueprintPermission.objects.for_requester(request, actual=True)
        .filter(object_type=PermissionObjectTypeChoices.zaak)
        .distinct()
        .values_list("policy", flat=True)
    )
    zaaktypen_policies = list(zaaktypen_policies)
    catalogi_urls = list({zt.catalogus for zt in zaaktypen})
    catalogi = {url: fetch_catalogus(url) for url in catalogi_urls}
    return [
        zaaktype
        for zaaktype in zaaktypen
        if [
            policy
            for policy in zaaktypen_policies
            if policy["catalogus"] == catalogi[zaaktype.catalogus].domein
            and policy["zaaktype_omschrijving"] == zaaktype.omschrijving
            and VA_ORDER[policy["max_va"]]
            >= VA_ORDER[zaaktype.vertrouwelijkheidaanduiding]
        ]
    ]


@cache_result("zaaktype:{url}", timeout=A_DAY)
def fetch_zaaktype(url: str) -> ZaakType:
    client = client_from_url(url)
    result = client.retrieve("zaaktype", url=url)
    return factory(ZaakType, result)


def get_zaaktype(url: str, request: Optional[Request] = None) -> Optional[ZaakType]:
    """
    Calls fetch_zaaktype, but filters the result on the user's permissions.
    """
    zaaktype = fetch_zaaktype(url)
    catalogus = fetch_catalogus(zaaktype.catalogus)

    if (
        (not request)
        or (getattr(request.auth, "has_all_reading_rights", False))
        or (getattr(request.user, "is_superuser", False))
    ):
        return zaaktype

    # filter out zaaktypen from permissions
    zaaktypen_policies = (
        BlueprintPermission.objects.for_requester(request, actual=True)
        .filter(object_type=PermissionObjectTypeChoices.zaak)
        .distinct()
        .values_list("policy", flat=True)
    )
    zaaktypen_policies = list(zaaktypen_policies)
    return (
        zaaktype
        if [
            policy
            for policy in zaaktypen_policies
            if policy["catalogus"] == catalogus.domein
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
        client, "statustype", request_kwargs={"params": {"zaaktype": zaaktype.url}}
    )
    statustypen = factory(StatusType, _statustypen)
    return statustypen


@cache_result("statustype:{url}", timeout=A_DAY)
def get_statustype(url: str) -> StatusType:
    client = client_from_url(url)
    status_type = client.retrieve("statustype", url=url)
    status_type = factory(StatusType, status_type)
    return status_type


@cache_result("zt:resultaattypen:{zaaktype.url}", timeout=A_DAY)
def get_resultaattypen(zaaktype: ZaakType) -> List[ResultaatType]:
    client = _client_from_object(zaaktype)
    resultaattypen = get_paginated_results(
        client,
        "resultaattype",
        request_kwargs={"params": {"zaaktype": zaaktype.url}},
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
        request_kwargs={"params": {"zaaktype": zaaktype.url}},
    )

    eigenschappen = factory(Eigenschap, eigenschappen)

    # resolve relations
    for eigenschap in eigenschappen:
        eigenschap.zaaktype = zaaktype

    return eigenschappen


@cache_result("eigenschap:{url}", timeout=A_DAY)
def get_eigenschap(url: str) -> Eigenschap:
    client = client_from_url(url)
    result = client.retrieve("eigenschap", url)
    return factory(Eigenschap, result)


def get_eigenschappen_for_zaaktypen(zaaktypen: List[ZaakType]) -> List[Eigenschap]:
    with parallel(max_workers=settings.MAX_WORKERS) as executor:
        _eigenschappen = executor.map(get_eigenschappen, zaaktypen)

    eigenschappen = sum(list(_eigenschappen), [])

    # transform values and remove duplicates
    eigenschappen_aggregated = []
    for eigenschap in eigenschappen:
        existing_eigenschappen = [
            e for e in eigenschappen_aggregated if e.naam == eigenschap.naam
        ]
        eigenschap_json_schema = convert_eigenschap_spec_to_json_schema(
            eigenschap.specificatie
        )
        differing_specs = []
        for e in existing_eigenschappen:
            existing_eigenschap_json_schema = convert_eigenschap_spec_to_json_schema(
                e.specificatie
            )
            differing_specs.append(
                eigenschap_json_schema != existing_eigenschap_json_schema
            )

        if len(differing_specs) > 0:
            if any(differing_specs):
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
    client = client_from_url(url)
    result = client.retrieve("roltype", url)
    return factory(RolType, result)


@cache_result("zt:roltypen:{zaaktype.url}:{omschrijving_generiek}", timeout=A_DAY)
def get_roltypen(zaaktype: ZaakType, omschrijving_generiek: str = "") -> list:
    query_params = {"zaaktype": zaaktype.url}
    if omschrijving_generiek:
        query_params.update({"omschrijvingGeneriek": omschrijving_generiek})
    client = _client_from_object(zaaktype)
    roltypen = get_paginated_results(
        client, "roltype", request_kwargs={"params": query_params}
    )
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
        client,
        "zaakinformatieobjecttype",
        request_kwargs={"params": {"zaaktype": zaaktype.url}},
    )
    urls = [
        iot["informatieobjecttype"]
        for iot in sorted(results, key=lambda iot: iot["volgnummer"])
    ]
    with parallel(max_workers=settings.MAX_WORKERS) as executor:
        results = list(executor.map(get_informatieobjecttype, urls))

    return results


@cache_result("informatieobjecttype:{url}", timeout=A_DAY)
def get_informatieobjecttype(url: str) -> InformatieObjectType:
    client = client_from_url(url)
    data = client.retrieve("informatieobjecttype", url=url)
    return factory(InformatieObjectType, data)


@cache_result("zt:besluittypen:{zaaktype.url}")
def get_besluittypen_for_zaaktype(zaaktype: ZaakType) -> List[BesluitType]:
    with parallel(max_workers=settings.MAX_WORKERS) as executor:
        results = executor.map(fetch_besluittype, zaaktype.besluittypen)
    return list(results)


@cache_result("zts:catalogi", timeout=AN_HOUR)
def get_catalogi() -> List[Catalogus]:
    """
    Fetch all catalogi from the ZTCs.

    """

    results = _get_from_catalogus("catalogus")
    catalogi = factory(Catalogus, results)
    return catalogi


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
        request_kwargs={"params": query, "headers": {"Accept-Crs": "EPSG:4326"}},
        minimum=minimum,
    )
    return _zaken


def get_zaken_all_paginated(
    client: ZGWClient,
    query_params: Dict = dict(),
) -> Tuple[List[Zaak], Dict]:
    """
    Fetch all zaken from the ZRCs in batches.
    Used to index Zaken in ES.
    Should not be used for searches with user permissions
    """
    response = client.list(
        "zaak",
        query_params=query_params,
        request_kwargs={"headers": {"Accept-Crs": "EPSG:4326"}},
    )
    zaken = factory(Zaak, response["results"])
    query_params = fetch_next_url_pagination(response, query_params=query_params)
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
        return get_paginated_results(
            client,
            "zaak",
            request_kwargs={
                "params": query_params,
                "headers": {"Accept-Crs": "EPSG:4326"},
            },
        )

    with parallel(max_workers=settings.MAX_WORKERS) as executor:
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
                client, resource, request_kwargs={"params": query}
            )
        return related_objects

    def _get_zaak(args):
        client, zaak_url = args
        return get_zaak(zaak_uuid=None, zaak_url=zaak_url, client=client)

    with parallel(max_workers=settings.MAX_WORKERS) as executor:
        results = executor.map(_get_related_objects, clients)

        job_args = []
        for client, related_objects in zip(clients, results):
            zaak_urls = set(ro["zaak"] for ro in related_objects)
            job_args += [(client, zaak_url) for zaak_url in zaak_urls]
        zaken_results = executor.map(_get_zaak, job_args)

    zaken = list(zaken_results)

    def _resolve_zaaktype(zaak):
        zaak.zaaktype = fetch_zaaktype(zaak.zaaktype)

    with parallel(max_workers=settings.MAX_WORKERS) as executor:
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


@cache_result("zaak:{bronorganisatie}:{identificatie}", timeout=AN_HOUR / 2)
def find_zaak(bronorganisatie: str, identificatie: str) -> Zaak:
    """
    Find the Zaak, uniquely identified by bronorganisatie & identificatie.

    """
    # try local search index first
    results = search_zaken(
        size=1,
        only_allowed=False,
        identificatie_keyword=identificatie,
        bronorganisatie=bronorganisatie,
    )
    if results:
        zaak = get_zaak(zaak_url=results[0].url)
    else:
        query = {"bronorganisatie": bronorganisatie, "identificatie": identificatie}
        # not in cache -> check it in all known ZRCs
        zrcs = Service.objects.filter(api_type=APITypes.zrc)
        zaak = None
        for zrc in zrcs:
            client = zrc.build_client()
            results = get_paginated_results(
                client,
                "zaak",
                request_kwargs={
                    "params": query,
                    "headers": {"Accept-Crs": "EPSG:4326"},
                },
            )

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
        client, "status", request_kwargs={"params": {"zaak": zaak.url}}
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


@cache_result("zaakeigenschappen:{zaak.url}", timeout=AN_HOUR)
def fetch_zaakeigenschappen(zaak: Zaak) -> List[ZaakEigenschap]:
    zrc_client = _client_from_object(zaak)
    zaak_eigenschappen = zrc_client.list("zaakeigenschap", zaak_uuid=zaak.uuid)
    return sorted(factory(ZaakEigenschap, zaak_eigenschappen), key=lambda zei: zei.naam)


def get_zaakeigenschappen(zaak: Zaak) -> List[ZaakEigenschap]:
    perf_logger.info("      Fetching eigenschappen for zaak %s", zaak.identificatie)

    zaak.zaaktype = (
        zaak.zaaktype
        if isinstance(zaak.zaaktype, ZaakType)
        else get_zaaktype(zaak.zaaktype)
    )
    eigenschappen = {
        eigenschap.url: eigenschap for eigenschap in get_eigenschappen(zaak.zaaktype)
    }
    zaak_eigenschappen = fetch_zaakeigenschappen(zaak)

    perf_logger.info(
        "      Done fetching eigenschappen for zaak %s", zaak.identificatie
    )

    # resolve relations
    for zaak_eigenschap in zaak_eigenschappen:
        zaak_eigenschap.eigenschap = eigenschappen[zaak_eigenschap.eigenschap]

    return zaak_eigenschappen


def fetch_zaak_eigenschap(zaak_eigenschap_url: str) -> ZaakEigenschap:
    client = client_from_url(zaak_eigenschap_url)
    zaak_eigenschap = client.retrieve("zaakeigenschap", url=zaak_eigenschap_url)
    zaak_eigenschap = factory(ZaakEigenschap, zaak_eigenschap)
    zaak_eigenschap.eigenschap = get_eigenschap(zaak_eigenschap.eigenschap)

    return zaak_eigenschap


def create_zaak_eigenschap(
    request: Optional[Request] = None,
    zaak_url: str = "",
    naam: str = "",
    waarde: str = "",
) -> Optional[ZaakEigenschap]:
    zaak = get_zaak(zaak_url=zaak_url)
    zaaktype = get_zaaktype(zaak.zaaktype, request=request)
    if not zaaktype:
        logger.info(
            "Zaaktype %s could not be retrieved for user with username '%s', aborting."
            % (zaak.zaaktype, request.user)
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

    zrc_client = client_from_url(zaak_url)
    zaak_eigenschap = zrc_client.create(
        "zaakeigenschap",
        {
            "zaak": zaak_url,
            "eigenschap": eigenschap_url,
            "waarde": waarde,
        },
        zaak_uuid=zaak_url.split("/")[-1],
    )
    return factory(ZaakEigenschap, zaak_eigenschap)


def update_zaak_eigenschap(
    zaak_eigenschap: ZaakEigenschap, data: dict, request: Optional[Request] = None
) -> ZaakEigenschap:
    zei = create_zaak_eigenschap(
        request=request,
        zaak_url=zaak_eigenschap.zaak,
        naam=zaak_eigenschap.naam,
        waarde=data["waarde"],
    )
    try:
        delete_zaak_eigenschap(zaak_eigenschap.url)
    except ClientError as exc:
        logger.info(
            "Could not delete zaakeigenschap {zaakeigenschap}.".format(
                zaakeigenschap=zaak_eigenschap.url
            ),
            exc_info=True,
        )
    return zei


def delete_zaak_eigenschap(zaak_eigenschap_url: str):
    client = client_from_url(zaak_eigenschap_url)
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
        client = client_from_url(zaak_url)

    if client is None:
        zrcs = Service.objects.filter(api_type=APITypes.zrc)
        result = None

        for zrc in zrcs:
            client = zrc.build_client()
            result = client.retrieve(
                "zaak",
                url=zaak_url,
                uuid=zaak_uuid,
                request_kwargs={"headers": {"Accept-Crs": "EPSG:4326"}},
            )

            if not result:
                continue
    else:
        result = client.retrieve(
            "zaak",
            url=zaak_url,
            uuid=zaak_uuid,
            request_kwargs={"headers": {"Accept-Crs": "EPSG:4326"}},
        )

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

    with parallel(max_workers=settings.MAX_WORKERS) as executor:
        results = list(executor.map(_fetch_zaak, zaak.relevante_andere_zaken))

    return results


@cache_result("zaak_objecten:{zaak.url}", timeout=AN_HOUR)
def get_zaakobjecten(zaak: Zaak) -> List[ZaakObject]:
    client = client_from_url(zaak.url)

    zaakobjecten = get_paginated_results(
        client,
        "zaakobject",
        request_kwargs={"params": {"zaak": zaak.url}},
    )

    return factory(ZaakObject, zaakobjecten)


def get_zaakobjecten_related_to_object(object_url: str) -> List[ZaakObject]:
    zrcs = Service.objects.filter(api_type=APITypes.zrc)
    results = []

    for zrc in zrcs:
        client = zrc.build_client()
        result = get_paginated_results(
            client, "zaakobject", request_kwargs={"params": {"object": object_url}}
        )

        if not result:
            continue
        else:
            results += factory(ZaakObject, result)

    return results


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


# @cache_result("rollen:{zaak.url}", alias="request", timeout=10)
def get_rollen(zaak: Zaak) -> List[Rol]:
    perf_logger.info("      Fetching rollen for zaak %s", zaak.identificatie)
    # fetch the rollen
    client = _client_from_object(zaak)
    _rollen = get_paginated_results(
        client, "rol", request_kwargs={"params": {"zaak": zaak.url}}
    )
    perf_logger.info("      Done fetching rollen for zaak %s", zaak.identificatie)

    rollen = factory(Rol, _rollen)

    return rollen


@cache_result("rol:{rol_url}", timeout=AN_HOUR)
def fetch_rol(rol_url: str) -> Rol:
    client = client_from_url(rol_url)
    rol = client.retrieve("rol", url=rol_url)

    rol = factory(Rol, rol)
    return rol


def create_rol(rol: Dict) -> Rol:
    zrc_client = client_from_url(rol["zaak"])
    rol = zrc_client.create("rol", rol)
    return factory(Rol, rol)


def delete_rol(rol_url: str, zaak: Zaak, user: Optional[User] = None):
    from zac.contrib.objects.oudbehandelaren.utils import register_old_behandelaar

    # fetch old rol and register it in the appropriate object before deleting
    register_old_behandelaar(zaak=zaak, rol_url=rol_url, user=user)
    invalidate_cache_fetch_oudbehandelaren(zaak)

    # delete rol
    zrc_client = client_from_url(rol_url)
    zrc_client.delete("rol", url=rol_url)


def update_rol(
    rol_url: str,
    new_rol: Dict,
    zaak: Zaak,
    user: Optional[User] = None,
) -> Rol:
    """
    Open zaak 1.8.x (CURRENT) does not allow patching/putting ROLlen.

    """
    # Destroy old rol
    delete_rol(rol_url, zaak, user=user)

    # Create new rol
    return create_rol(new_rol)


def update_medewerker_identificatie_rol(rol_url: str, zaak: Zaak) -> Optional[Rol]:
    rol = fetch_rol(rol_url)

    if rol.betrokkene_type != RolTypes.medewerker or rol.betrokkene:
        return

    # if there is some part of a name - do nothing.
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

    if not user.get_full_name() or user.get_full_name() == user.username:
        return

    from .api.serializers import RolSerializer

    new_rol_data = RolSerializer(instance=rol, context={"user": user}).data
    return update_rol(rol_url, new_rol_data, zaak)


def fetch_zaak_informatieobject(zaak_informatieobject_url: str) -> ZaakInformatieObject:
    client = client_from_url(zaak_informatieobject_url)
    zaak_informatieobject = client.retrieve(
        "zaak_informatieobject_url", url=zaak_informatieobject_url
    )
    zaak_informatieobject = factory(ZaakInformatieObject, zaak_informatieobject)
    return zaak_informatieobject


def get_zaakinformatieobjecten_related_to_informatieobject(
    informatieobject_url: str,
) -> List[ZaakInformatieObject]:
    zrcs = Service.objects.filter(api_type=APITypes.zrc)
    results = []

    for zrc in zrcs:
        client = zrc.build_client()
        result = client.list(
            "zaakinformatieobject",
            query_params={"informatieobject": informatieobject_url},
        )

        if not result:
            continue
        else:
            results += result

    return factory(ZaakInformatieObject, results)


def get_zaak_informatieobjecten(zaak: Zaak) -> List[ZaakInformatieObject]:
    client = _client_from_object(zaak)
    zaak_informatieobjecten = client.list(
        "zaakinformatieobject", query_params={"zaak": zaak.url}
    )
    return factory(ZaakInformatieObject, zaak_informatieobjecten)


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

        _rollen = get_paginated_results(
            client, "rol", request_kwargs={"params": query_params}
        )

        all_rollen += factory(Rol, _rollen)

    return all_rollen


###################################################
#                       DRC                       #
###################################################


def _fetch_document(url: str) -> Response:
    """
    Retrieve document by URL from DRC or cache.
    """
    cache_key = f"document:{url}"
    if cache_key in cache and (response := cache.get(cache_key)):
        return response
    client = client_from_url(url)
    headers = client.auth.credentials()
    response = requests.get(url, headers=headers)
    cache_document(url, response)
    return response


def fetch_documents(zios: List[str]) -> Tuple[List[Document], List[str]]:
    with parallel(max_workers=settings.MAX_WORKERS) as executor:
        responses = executor.map(lambda url: _fetch_document(url), zios)
    documenten = []
    gone = []
    for response, zio in zip(responses, zios):
        if response.status_code == 200:
            documenten.append(response.json())
        else:
            logger.warning("Document with url %s can't be retrieved." % zio)
            gone.append(zio)
    return factory(Document, documenten), gone


@cache_result("get_all_informatieobjecttypen", timeout=A_DAY)
def get_all_informatieobjecttypen() -> Dict[str, InformatieObjectType]:
    logger.debug("Retrieving ZTC configuration for informatieobjecttypen")
    ztcs = Service.objects.filter(api_type=APITypes.ztc)
    all_informatieobjecttypen = []
    for ztc in ztcs:
        client = ztc.build_client()
        results = get_paginated_results(client, "informatieobjecttype")
        all_informatieobjecttypen += results
    informatieobjecttypen = {
        iot["url"]: factory(InformatieObjectType, iot)
        for iot in all_informatieobjecttypen
    }
    return informatieobjecttypen


def resolve_documenten_informatieobjecttypen(
    documents: List[Document],
) -> List[Document]:

    unresolved = {
        document.informatieobjecttype
        for document in documents
        if type(document.informatieobjecttype) == str
    }

    # If they are already resolved (?) - skip rest.
    if not unresolved:
        return documents

    informatieobjecttypen = get_all_informatieobjecttypen()

    # resolve relations
    for document in documents:
        if type(document.informatieobjecttype) == str:
            document.informatieobjecttype = informatieobjecttypen[
                document.informatieobjecttype
            ]
    return documents


def get_documenten(zaak: Zaak, use_elastic: bool = True) -> List[Document]:
    ## Deprecate in favor of elasticsearch for performance:
    logger.warning(
        "DEPRECATED WARNING - please use zac.elasticsearch.searches.search_informatieobjects instead for performance."
    )
    logger.debug("Retrieving documents linked to zaak %r", zaak)

    # get zaakinformatieobjecten
    zaak_informatieobjecten = get_zaak_informatieobjecten(zaak)

    # retrieve the documents themselves, in parallel
    ios = [zio.informatieobject for zio in zaak_informatieobjecten]
    logger.debug("Fetching %d documents", len(zaak_informatieobjecten))

    # Add version to zio_url if found in doc_versions
    found, gone = fetch_documents(ios)

    return found


@cache_result("document:{bronorganisatie}:{identificatie}:{versie}")
def find_document(
    bronorganisatie: str, identificatie: str, versie: Optional[int] = None
) -> Document:
    """
    Find the document uniquely identified by bronorganisatie and identificatie.
    """
    # not in cache -> check it first in ES and then in all known DRCs
    query = {"bronorganisatie": bronorganisatie, "identificatie": identificatie}
    result = None
    results = search_informatieobjects(**query)
    if results:
        document_furl = furl(results[0].url).add({"versie": versie})
        response = _fetch_document(document_furl.url)  # fetch latest version
        response.raise_for_status()
        result = response.json()

    else:
        drcs = Service.objects.filter(api_type=APITypes.drc)
        for drc in drcs:
            client = drc.build_client()
            results = get_paginated_results(
                client, "enkelvoudiginformatieobject", request_kwargs={"params": query}
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
                candidates = [
                    result for result in results if result["versie"] == versie
                ]
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
    client = client_from_url(url)

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
    invalidate_document_url_cache(document.url)
    invalidate_document_other_cache(document)

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


@cache_result("audit_trail:{document_url}", timeout=A_DAY)
def fetch_document_audit_trail(document_url: str) -> List[AuditTrailData]:
    drc_client = client_from_url(document_url)
    doc_uuid = furl(document_url).path.segments[-1]
    try:
        audit_trail = drc_client.list(
            "audittrail", enkelvoudiginformatieobject_uuid=doc_uuid
        )
    except ClientError:
        logger.warning(
            "No audit trail found for {document}".format(document=document_url)
        )
        audit_trail = []
    return factory(AuditTrailData, audit_trail)


def fetch_latest_audit_trail_data_document(
    document_url: str,
) -> Optional[AuditTrailData]:
    ats = fetch_document_audit_trail(document_url)
    ats = sorted(ats, key=lambda obj: obj.aanmaakdatum, reverse=True)
    at = [edit for edit in ats if edit.was_bumped] or ats
    if at:
        return at[0]
    return None


def get_documenten_all_paginated(
    client: ZGWClient,
    query_params: dict = {},
) -> Tuple[List[Document], dict]:
    """
    Fetch all enkelvoudiginformatieobjects from the DRCs in batches.
    Used to index documenten in ES.

    """
    response = client.list("enkelvoudiginformatieobject", query_params=query_params)
    documenten = factory(Document, response["results"])
    query_params = fetch_next_url_pagination(response, query_params=query_params)
    return documenten, query_params


###################################################
#                       BRC                       #
###################################################


def get_besluiten(zaak: Zaak) -> List[Besluit]:
    query = {"zaak": zaak.url}
    brcs = Service.objects.filter(api_type=APITypes.brc)

    results = []
    for brc in brcs:
        client = brc.build_client()
        results += get_paginated_results(
            client, "besluit", request_kwargs={"params": query}
        )

    besluiten = factory(Besluit, results)

    # resolve besluittypen
    _besluittypen = {besluit.besluittype for besluit in besluiten}
    with parallel(max_workers=settings.MAX_WORKERS) as executor:
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


def add_string_representation(func):
    """
    Until string representations are supported by objects
    use this function to add stringRepresentation based on labels
    of objecttypes.

    """

    def _add_string_representation_field(obj: Dict, objecttypes: Dict) -> Dict:
        ot = (
            objecttypes.get(obj["type"])
            if isinstance(obj["type"], str)
            else obj["type"]
        )
        if (
            ot
            and (labels := ot["labels"].get("stringRepresentation", []))
            and (obj.get("record", {}).get("data", {}).keys())
        ):
            # get the values of the original fields from the object
            values = [
                obj["record"]["data"].get(label[7:], "")
                if "field__" in label
                else label
                for label in labels
                if label
            ]
            obj["stringRepresentation"] = "".join([val for val in values if val])
        else:
            obj["stringRepresentation"] = "Objectnaam niet beschikbaar."
        return obj

    def _fetch_object_types() -> Dict[str, Dict]:
        return {ot["url"]: ot for ot in fetch_objecttypes()}

    def if_list(objs: List[Dict]) -> List[Dict]:
        ots = _fetch_object_types()
        return [_add_string_representation_field(obj, ots) for obj in objs]

    def if_dict(objs: Dict) -> Dict:
        if "results" in objs and objs["results"]:
            ots = _fetch_object_types()
            objs["results"] = [
                _add_string_representation_field(obj, ots) for obj in objs["results"]
            ]
            return objs
        elif "results" not in objs:
            return _add_string_representation_field(objs, _fetch_object_types())
        return objs

    @wraps(func)
    def wrapper(*args, **kwds):
        objs = func(*args, **kwds)
        mapping = {
            list: lambda objects: if_list(objects),
            dict: lambda objects: if_dict(objects),
        }
        return mapping[type(objs)](objs)

    return wrapper


def get_objects_client() -> Client:
    config = CoreConfig.get_solo()
    object_api = config.primary_objects_api
    if not object_api:
        raise RuntimeError("No objects API has been configured yet.")
    object_api_client = object_api.build_client()
    return object_api_client


def get_objecttypes_client() -> Client:
    config = CoreConfig.get_solo()
    objecttypes_api = config.primary_objecttypes_api
    if not objecttypes_api:
        raise RuntimeError("No objecttypes API has been configured yet.")
    objecttypes_api_client = objecttypes_api.build_client()
    return objecttypes_api_client


@add_string_representation
def create_object(data: Dict) -> Dict:
    client = get_objects_client()
    object = client.create("object", data=data)
    return object


@add_string_representation
@cache_result("object:{url}", timeout=A_DAY)
def fetch_object(url: str, client: Optional[Client] = None) -> dict:
    if not client:
        client = get_objects_client()
    retrieved_item = client.retrieve("object", url=url)
    retrieved_item["type"] = fetch_objecttype(retrieved_item["type"])
    return retrieved_item


def fetch_objects(
    urls: List[str], max_workers: int = settings.MAX_WORKERS
) -> List[Dict]:
    object_api_client = get_objects_client()

    def _fetch_object(url):
        return fetch_object(url, client=object_api_client)

    with parallel(max_workers=max_workers) as executor:
        retrieved_objects = list(executor.map(_fetch_object, urls))

    return retrieved_objects


def update_object_record_data(
    object: Dict, data: Dict, user: Optional[User] = None
) -> Dict:
    client = get_objects_client()
    new_data = {
        "record": {
            **object["record"],
            "data": data,
            "correctionFor": object["record"]["index"],
            "correctedBy": user.username if user else "service-account",
        }
    }
    obj = client.partial_update(
        "object",
        uuid=object["uuid"],
        data=new_data,
    )
    return obj


@cache_result("objecttype:{url}", timeout=AN_HOUR)
def fetch_objecttype(url: str, client: Optional[Client] = None) -> dict:
    if not client:
        client = get_objecttypes_client()
    object_type = client.retrieve("objecttype", url=url)

    return object_type


@cache_result("objecttype:all", timeout=AN_HOUR)
def fetch_objecttypes() -> List[dict]:
    client = get_objecttypes_client()
    objecttypes_data = client.list("objecttype")

    return objecttypes_data


@cache_result("objecttype:{uuid}:{version}", timeout=A_DAY)
def fetch_objecttype_version(uuid: str, version: int) -> dict:
    client = get_objecttypes_client()
    objecttypes_version_data = client.retrieve(
        "objectversion", **{"objecttype_uuid": uuid, "version": version}
    )

    return objecttypes_version_data


def search_objects(
    filters: dict, query_params: Optional[Dict] = None
) -> Tuple[List[dict], Dict]:
    client = get_objects_client()
    operation_id = "object_search"
    url = get_operation_url(client.schema, operation_id, base_url=client.base_url)
    query_params = query_params if query_params else dict()
    url = furl(url).set(query_params).url
    response = add_string_representation(client.operation)(
        url=url, operation_id=operation_id, query_params=query_params, data=filters
    )

    query_params = fetch_next_url_pagination(response, query_params=query_params)
    return response, query_params


def fetch_objects_all_paginated(
    client: ZGWClient, query_params: Dict = dict
) -> Tuple[List[dict], Dict]:
    response = add_string_representation(client.list)(
        "object", query_params=query_params
    )
    query_params = fetch_next_url_pagination(response, query_params=query_params)
    return response, query_params


def relate_object_to_zaak(relation_data: dict) -> dict:
    zrc_client = Service.get_client(relation_data["zaak"])
    assert zrc_client is not None, "ZRC client not found"

    response = zrc_client.create(
        "zaakobject",
        relation_data,
    )
    return response


def fetch_zaakobject(zaak_object_url: str) -> ZaakObject:
    client = client_from_url(zaak_object_url)
    zaak_object = client.retrieve("zaakobject", url=zaak_object_url)
    return factory(ZaakObject, zaak_object)


def delete_zaakobject(zaak_object_url: str):
    client = client_from_url(zaak_object_url)
    client.delete("zaakobject", url=zaak_object_url)


def delete_zaakobjecten_of_object(object_url: str):
    services = Service.objects.filter(api_type=APITypes.zrc)
    zon = []
    for zrc in services:
        client = zrc.build_client()
        _zon = client.list("zaakobject", query_params={"object": object_url})
        zon += _zon

    with parallel(max_workers=settings.MAX_WORKERS) as executor:
        executor.map(delete_zaakobject, [zo["url"] for zo in zon])