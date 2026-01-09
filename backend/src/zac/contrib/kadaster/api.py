from typing import List, Optional

from django.utils.translation import gettext_lazy as _

from furl import furl
from rest_framework import status
from rest_framework.exceptions import APIException, NotFound
from zds_client.schema import get_operation_url
from zgw_consumers.api_models.base import factory

from zac.contrib.kadaster.bag import A_DAY, LocationServer
from zac.contrib.kadaster.client import override_zds_client
from zac.contrib.kadaster.data import AddressSearchResponse, Pand, Verblijfsobject
from zac.contrib.kadaster.models import KadasterConfig
from zac.utils.decorators import cache, optional_service
from zac.zgw_client import ZGWClient


def get_location_server_client() -> LocationServer:
    return LocationServer()


def get_bag_client() -> ZGWClient:
    config = KadasterConfig.get_solo()
    assert config.service, "A service must be configured first"
    service = config.service
    client = service.build_client()
    client = override_zds_client(
        client,
    )
    return client


@optional_service
def get_address_suggestions(query: str) -> List[AddressSearchResponse]:
    client = get_location_server_client()
    results = client.suggest({"q": query, "fq": "bron:bag AND type:adres"})
    # Fix ugly spellcheck results wtf
    if "spellcheck" in results:
        search_terms = results["spellcheck"]["suggestions"][::2]
        suggestions = results["spellcheck"]["suggestions"][1::2]
        results["spellcheck"]["suggestions"] = [
            {"search_term": search_term, **suggestion}
            for search_term, suggestion in zip(search_terms, suggestions)
        ]
    return factory(AddressSearchResponse, results)


@cache("adres:{address_id}", timeout=A_DAY)
def _get_address_lookup(address_id: str) -> dict:
    client = get_location_server_client()
    results = client.lookup(address_id)
    if not results["numFound"] == 1:
        raise APIException(
            detail="Found %s addresses. Invalid ID provided." % results["numFound"],
            code="invalid",
        )
    return results["docs"][0]


@cache("kadaster:{url}", timeout=A_DAY)
def _do_request(
    client,
    url: str,
    operation_id: str,
    method="GET",
    expected_status=200,
    headers: Optional[dict] = None,
) -> dict:
    results = client.request(
        url,
        operation_id,
        method=method,
        expected_status=expected_status,
        headers=headers,
    )
    return results


def _make_request(
    operation_id: str,
    path_params: Optional[dict] = None,
    query_params: Optional[dict] = None,
    method="GET",
    expected_status=200,
    headers: Optional[dict] = None,
) -> dict:
    client = get_bag_client()
    if not path_params:
        path_params = {}
    url = get_operation_url(
        client.schema,
        operation_id,
        **path_params,
    )
    if query_params:
        url = furl(url).add(query_params).url
    results = _do_request(
        client,
        url,
        operation_id,
        method=method,
        expected_status=expected_status,
        headers=headers,
    )
    return results


def _get_adres(adresseerbaarobjectidentificatie: int) -> dict:
    results = _make_request(
        "bevraagAdressen",
        query_params={
            "adresseerbaarObjectIdentificatie": adresseerbaarobjectidentificatie,
        },
    )
    return results


def _get_adresseerbaarobject(adresseerbaarobjectidentificatie: int) -> dict:
    results = _make_request(
        "bevragenAdresseerbaarObject",
        path_params={
            "adresseerbaarObjectIdentificatie": adresseerbaarobjectidentificatie
        },
        headers={"Accept-CRS": "epsg:28992"},
    )
    return results


def get_pand(pandidentificatie: str) -> dict:
    results = _make_request(
        "pandIdentificatie",
        path_params={"identificatie": pandidentificatie},
        headers={"Accept-CRS": "epsg:28992"},
    )
    return results


@optional_service
def find_pand(address_id: str) -> Optional[Pand]:
    doc = _get_address_lookup(address_id)
    adres = _get_adres(doc["adresseerbaarobject_id"])
    assert len(adres["_embedded"]["adressen"]) == 1
    panden = [
        pand_id for pand_id in adres["_embedded"]["adressen"][0]["pandIdentificaties"]
    ]
    assert len(panden) == 1
    pand = get_pand(panden[0])
    data = {
        "adres": {
            "straatnaam": doc["straatnaam"],
            "nummer": doc["huisnummer"],
            "gemeentenaam": doc["gemeentenaam"],
            "postcode": doc.get("postcode", ""),
            "provincienaam": doc.get("provincienaam", ""),
        },
        "bagObject": {
            "url": pand["_links"]["self"]["href"],
            "geometrie": pand["pand"]["geometrie"],
            "status": pand["pand"]["status"],
            "oorspronkelijkBouwjaar": pand["pand"]["oorspronkelijkBouwjaar"],
        },
    }
    return factory(Pand, data)


@optional_service
def get_verblijfsobject(address_id: str) -> Optional[Verblijfsobject]:
    doc = _get_address_lookup(address_id)
    ao = _get_adresseerbaarobject(doc["adresseerbaarobject_id"])
    if not ao.get("verblijfsobject"):
        raise NotFound(
            detail=_(
                "verblijfsobject not found for adresseerbaarobject_id {adresseerbaarobject_id}".format(
                    adresseerbaarobject_id=doc["adresseerbaarobject_id"]
                )
            )
        )
    data = {
        "adres": {
            "straatnaam": doc["straatnaam"],
            "nummer": doc["huisnummer"],
            "gemeentenaam": doc["gemeentenaam"],
            "postcode": doc.get("postcode", ""),
            "provincienaam": doc.get("provincienaam", ""),
        },
        "bagObject": {
            "url": ao["verblijfsobject"]["_links"]["self"]["href"],
            "geometrie": ao["verblijfsobject"]["verblijfsobject"]["geometrie"],
            "status": ao["verblijfsobject"]["verblijfsobject"]["status"],
            "oppervlakte": ao["verblijfsobject"]["verblijfsobject"]["oppervlakte"],
        },
    }
    return factory(Verblijfsobject, data)


def get_nummeraanduiding(nummeraanduidingidentificatie: str) -> dict:
    results = _make_request(
        "nummeraanduidingIdentificatie",
        path_params={"nummeraanduidingIdentificatie": nummeraanduidingidentificatie},
    )
    return results
