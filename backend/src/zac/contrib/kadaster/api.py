from typing import List, Optional

from django.utils.translation import gettext_lazy as _

from rest_framework import status
from rest_framework.exceptions import NotFound
from zds_client.schema import get_operation_url
from zgw_consumers.api_models.base import factory
from zgw_consumers.client import ZGWClient

from zac.utils.decorators import cache, optional_service

from .bag import A_DAY, LocationServer
from .data import AddressSearchResponse, Pand, Verblijfsobject
from .decorators import catch_bag_zdserror
from .exceptions import KadasterAPIException
from .models import KadasterConfig


def get_location_server_client() -> LocationServer:
    return LocationServer()


def get_bag_client() -> ZGWClient:
    config = KadasterConfig.get_solo()
    assert config.service, "A service must be configured first"
    service = config.service
    client = service.build_client()
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
        raise KadasterAPIException(
            detail="Invalid ID provided.",
            code="invalid",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    return results["docs"][0]


@catch_bag_zdserror
@cache("kadaster:{url}", timeout=A_DAY)
def _do_request(
    client, url: str, operation_id: str, method="GET", expected_status=200
) -> dict:
    results = client.request(url, operation_id, method="GET", expected_status=200)
    return results


def _make_request(
    operation_id: str, path_params: dict, method="GET", expected_status=200
) -> dict:
    client = get_bag_client()
    url = get_operation_url(
        client.schema,
        operation_id,
        **path_params,
    )
    results = _do_request(
        client, url, operation_id, method=method, expected_status=expected_status
    )
    return results


def _get_adresseerbaarobject(adresseerbaarobjectidentificatie: int) -> dict:
    results = _make_request(
        "raadpleegAdresseerbaarobject",
        path_params={
            "adresseerbaarobjectidentificatie": adresseerbaarobjectidentificatie
        },
    )
    return results


def get_pand(pandidentificatie: str) -> dict:
    results = _make_request(
        "raadpleegPand", path_params={"pandidentificatie": pandidentificatie}
    )
    return results


@optional_service
def find_pand(address_id: str) -> Optional[Pand]:
    doc = _get_address_lookup(address_id)
    adresseerbaarobject = _get_adresseerbaarobject(doc["adresseerbaarobject_id"])
    panden = [pand_id for pand_id in adresseerbaarobject["pandIdentificaties"]]
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
            "geometrie": pand["geometrie"],
            "status": pand["status"],
            "oorspronkelijkBouwjaar": pand["oorspronkelijkBouwjaar"],
        },
    }
    return factory(Pand, data)


@optional_service
def get_verblijfsobject(address_id: str) -> Optional[Verblijfsobject]:
    doc = _get_address_lookup(address_id)
    ao = _get_adresseerbaarobject(doc["adresseerbaarobject_id"])
    if not ao["type"] == "verblijfsobject":
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
            "url": ao["_links"]["self"]["href"],
            "geometrie": ao["geometrie"],
            "status": ao["status"],
            "oppervlakte": ao["oppervlakte"],
        },
    }
    return factory(Verblijfsobject, data)


def get_nummeraanduiding(nummeraanduidingidentificatie: str) -> dict:
    results = _make_request(
        "raadpleegNummeraanduiding",
        path_params={"nummeraanduidingidentificatie": nummeraanduidingidentificatie},
    )
    return results
