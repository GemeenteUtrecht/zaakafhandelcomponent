import os
from unittest.mock import patch

from django.urls import reverse

import requests_mock
from furl import furl
from rest_framework.test import APITransactionTestCase
from zgw_consumers.constants import APITypes, AuthTypes

from zac.accounts.tests.factories import SuperUserFactory
from zac.core.tests.utils import ClearCachesMixin
from zac.tests import ServiceFactory
from zac.tests.compat import generate_oas_component, mock_service_oas_get

from ..models import KadasterConfig

KADASTER_API_ROOT = "https://some-kadaster.nl/lvbag/individuelebevragingen/v2/"
LOCATION_SERVER_ROOT = "https://location-server-kadaster.nl/"


@patch.dict(os.environ, {"DEBUG": "False"})
@requests_mock.Mocker()
class KadasterAPITests(ClearCachesMixin, APITransactionTestCase):
    def setUp(self):
        super().setUp()
        service = ServiceFactory.create(
            label="kadaster",
            api_type=APITypes.orc,
            api_root=KADASTER_API_ROOT,
            auth_type=AuthTypes.api_key,
            header_key="x-api-key",
            header_value="some-secret-key",
        )

        config = KadasterConfig.get_solo()
        config.locatieserver = LOCATION_SERVER_ROOT
        config.service = service
        config.save()
        self.super_user = SuperUserFactory.create()
        self.client.force_authenticate(self.super_user)

    def test_user_not_logged_in_get_address(self, m):
        self.client.logout()
        url = furl(reverse("kadaster:adres-autocomplete"))
        url.args["q"] = "some-street"

        response = self.client.get(url.url)
        self.assertEqual(response.status_code, 403)

    def test_user_not_logged_in_find_pand(self, m):
        self.client.logout()
        address_id = "adr-09asnd9as0ndas09dnas09ndsa"
        url = furl(reverse("kadaster:adres-pand"))
        url.args["id"] = address_id

        response = self.client.get(url.url)
        self.assertEqual(response.status_code, 403)

    def test_user_not_logged_in_get_verblijfsobject(self, m):
        self.client.logout()
        address_id = "adr-09asnd9as0ndas09dnas09ndsa"
        url = furl(reverse("kadaster:adres-verblijfsobject"))
        url.args["id"] = address_id

        response = self.client.get(url.url)
        self.assertEqual(response.status_code, 403)

    def test_get_address_suggestions(self, m):
        search_term = "Some-street"
        response = {
            "response": {
                "numFound": 1,
                "start": 0,
                "maxScore": 25.37018,
                "docs": [
                    {
                        "type": "adres",
                        "weergavenaam": "Some-street 11, 9999XX Some-city",
                        "id": "adr-09asnd9as0ndas09dnas09ndsa",
                        "score": 25.37018,
                    }
                ],
            },
            "highlighting": {
                "adr-09asnd9as0ndas09dnas09ndsa": {
                    "suggest": ["<b>Some-street</b> <b>11</b>, <b>9999XX</b> Some-city"]
                }
            },
            "spellcheck": {
                "suggestions": [
                    "some-street",
                    {
                        "numFound": 2,
                        "startOffset": 0,
                        "endOffset": 9,
                        "suggestion": ["some-streets", "some-streed"],
                    },
                ],
                "collations": [],
            },
        }

        # Mock locatie server response
        m.get(
            f"{LOCATION_SERVER_ROOT}suggest?q={search_term}&fq=bron:bag%20AND%20type:adres",
            json=response,
        )

        url = furl(reverse("kadaster:adres-autocomplete"))
        url.args["q"] = "some-street"

        response = self.client.get(url.url)
        self.assertEqual(response.status_code, 200)
        results = response.json()
        self.assertEqual(
            results,
            {
                "response": {
                    "numFound": 1,
                    "start": 0,
                    "maxScore": 25.37018,
                    "docs": [
                        {
                            "type": "adres",
                            "weergavenaam": "Some-street 11, 9999XX Some-city",
                            "id": "adr-09asnd9as0ndas09dnas09ndsa",
                            "score": 25.37018,
                        }
                    ],
                },
                "spellcheck": {
                    "suggestions": [
                        {
                            "searchTerm": "some-street",
                            "numFound": 2,
                            "startOffset": 0,
                            "endOffset": 9,
                            "suggestion": ["some-streets", "some-streed"],
                        }
                    ]
                },
            },
        )

    def test_fail_get_address_suggestions(self, m):
        search_term = "Some-street"

        # Mock locatie server response
        m.get(
            f"{LOCATION_SERVER_ROOT}suggest?q={search_term}&fq=bron:bag%20AND%20type:adres",
            status_code=400,
        )

        url = furl(reverse("kadaster:adres-autocomplete"))
        url.args["q"] = "some-street"

        response = self.client.get(url.url)
        detail = response.json()["detail"]
        self.assertEqual(
            detail,
            "400 Client Error: None for url: https://location-server-kadaster.nl/suggest?q=some-street&fq=bron%3Abag+AND+type%3Aadres",
        )
        self.assertEqual(response.status_code, 400)

    def test_fail_get_address_lookup(self, m):
        address_id = "adr-09asnd9as0ndas09dnas09ndsa"
        m.get(f"{LOCATION_SERVER_ROOT}lookup?id={address_id}", status_code=404)

        url = furl(reverse("kadaster:adres-pand"))
        url.args["id"] = address_id

        response = self.client.get(url.url)
        detail = response.json()["detail"]
        self.assertEqual(
            detail,
            "404 Client Error: None for url: https://location-server-kadaster.nl/lookup?id=adr-09asnd9as0ndas09dnas09ndsa",
        )
        self.assertEqual(response.status_code, 404)

    def test_fail_get_address_lookup_too_many_found(self, m):
        address_id = "adr-09asnd9as0ndas09dnas09ndsa"
        num_found = 2
        response = {"response": {"numFound": num_found}}
        m.get(f"{LOCATION_SERVER_ROOT}lookup?id={address_id}", json=response)

        url = furl(reverse("kadaster:adres-pand"))
        url.args["id"] = address_id

        response = self.client.get(url.url)
        detail = response.json()["detail"]
        self.assertEqual(
            detail,
            "Found %s addresses. Invalid ID provided." % num_found,
        )
        self.assertEqual(response.status_code, 500)

    def test_find_pand(self, m):
        # Mock locatie server lookup response
        address_id = "adr-09asnd9as0ndas09dnas09ndsa"
        adresseerbaarobject_id = "9999999999999991"
        lookup_response = {
            "response": {
                "numFound": 1,
                "start": 0,
                "maxScore": 99,
                "docs": [
                    {
                        "bron": "BAG",
                        "woonplaatscode": "9999",
                        "type": "adres",
                        "woonplaatsnaam": "Some-city",
                        "wijkcode": "WK999999",
                        "huis_nlt": "9999",
                        "openbareruimtetype": "Weg",
                        "buurtnaam": "Some-neighborhood",
                        "gemeentecode": "9999",
                        "rdf_seealso": "http://some-bag.nl/bag/id/nummeraanduiding/9999999999999992",
                        "weergavenaam": "Some-street 99, 9999XX Some-city",
                        "straatnaam_verkort": "Some-street",
                        "id": address_id,
                        "gekoppeld_perceel": ["SMC-C-9998", "SMC-C-9999"],
                        "gemeentenaam": "Some-municipality",
                        "buurtcode": "BU99999999",
                        "wijknaam": "Some-wijk 99 Some-city",
                        "identificatie": "9999999999999991-9999999999999992",
                        "openbareruimte_id": "9999999999999993",
                        "waterschapsnaam": "Some-waterschap",
                        "provinciecode": "PV99",
                        "postcode": "9999XX",
                        "provincienaam": "Some-province",
                        "centroide_ll": "POINT(9 9)",
                        "nummeraanduiding_id": "9999999999999992",
                        "waterschapscode": "99",
                        "adresseerbaarobject_id": adresseerbaarobject_id,
                        "huisnummer": 99,
                        "provincieafkorting": "SP",
                        "centroide_rd": "POINT(0 0)",
                        "straatnaam": "Some-street",
                    }
                ],
            }
        }
        m.get(f"{LOCATION_SERVER_ROOT}lookup?id={address_id}", json=lookup_response)

        # mock kadaster api service
        mock_service_oas_get(m, KADASTER_API_ROOT, "kadaster")

        # mock adresseerbaar object from kadaster
        pand_id = "9999999999999994"
        adres = generate_oas_component(
            "kadaster",
            "schemas/Adres",
            AdresseerbaarObjectIdentificatie=adresseerbaarobject_id,
            pandIdentificaties=[pand_id],
        )
        m.get(
            f"{KADASTER_API_ROOT}adressen?adresseerbaarObjectIdentificatie={adresseerbaarobject_id}",
            json={"_embedded": {"adressen": [adres]}},
        )

        # mock pand from kadaster
        pand = generate_oas_component(
            "kadaster",
            "schemas/Pand",
            oorspronkelijkBouwjaar=2023,
            identificatie=pand_id,
            geometrie=[],
        )
        m.get(
            f"{KADASTER_API_ROOT}panden/{pand_id}",
            json={
                "pand": pand,
                "_links": {"self": {"href": f"{KADASTER_API_ROOT}panden/{pand_id}"}},
            },
        )

        url = furl(reverse("kadaster:adres-pand"))
        url.args["id"] = address_id

        response = self.client.get(url.url)
        self.assertEqual(response.status_code, 200)
        results = response.json()
        self.assertEqual(
            results,
            {
                "adres": {
                    "straatnaam": "Some-street",
                    "nummer": "99",
                    "gemeentenaam": "Some-municipality",
                    "postcode": "9999XX",
                    "provincienaam": "Some-province",
                },
                "bagObject": {
                    "url": f"{KADASTER_API_ROOT}panden/{pand_id}",
                    "geometrie": pand["geometrie"],
                    "status": pand["status"],
                    "oorspronkelijkBouwjaar": pand["oorspronkelijkBouwjaar"],
                },
            },
        )

    def test_find_pand_hit_cache(self, m):
        # Mock locatie server lookup response
        address_id = "adr-09asnd9as0ndas09dnas09ndsa"
        adresseerbaarobject_id = "9999999999999991"
        lookup_response = {
            "response": {
                "numFound": 1,
                "start": 0,
                "maxScore": 99,
                "docs": [
                    {
                        "bron": "BAG",
                        "woonplaatscode": "9999",
                        "type": "adres",
                        "woonplaatsnaam": "Some-city",
                        "wijkcode": "WK999999",
                        "huis_nlt": "9999",
                        "openbareruimtetype": "Weg",
                        "buurtnaam": "Some-neighborhood",
                        "gemeentecode": "9999",
                        "rdf_seealso": "http://some-bag.nl/bag/id/nummeraanduiding/9999999999999992",
                        "weergavenaam": "Some-street 99, 9999XX Some-city",
                        "straatnaam_verkort": "Some-street",
                        "id": address_id,
                        "gekoppeld_perceel": ["SMC-C-9998", "SMC-C-9999"],
                        "gemeentenaam": "Some-municipality",
                        "buurtcode": "BU99999999",
                        "wijknaam": "Some-wijk 99 Some-city",
                        "identificatie": "9999999999999991-9999999999999992",
                        "openbareruimte_id": "9999999999999993",
                        "waterschapsnaam": "Some-waterschap",
                        "provinciecode": "PV99",
                        "postcode": "9999XX",
                        "provincienaam": "Some-province",
                        "centroide_ll": "POINT(9 9)",
                        "nummeraanduiding_id": "9999999999999992",
                        "waterschapscode": "99",
                        "adresseerbaarobject_id": adresseerbaarobject_id,
                        "huisnummer": 99,
                        "provincieafkorting": "SP",
                        "centroide_rd": "POINT(0 0)",
                        "straatnaam": "Some-street",
                    }
                ],
            }
        }
        m.get(f"{LOCATION_SERVER_ROOT}lookup?id={address_id}", json=lookup_response)

        # mock kadaster api service
        mock_service_oas_get(m, KADASTER_API_ROOT, "kadaster")

        # mock adresseerbaar object from kadaster
        pand_id = "9999999999999994"
        adres = generate_oas_component(
            "kadaster",
            "schemas/Adres",
            AdresseerbaarObjectIdentificatie=adresseerbaarobject_id,
            pandIdentificaties=[pand_id],
        )
        m.get(
            f"{KADASTER_API_ROOT}adressen?adresseerbaarObjectIdentificatie={adresseerbaarobject_id}",
            json={"_embedded": {"adressen": [adres]}},
        )

        # mock pand from kadaster
        pand = generate_oas_component(
            "kadaster",
            "schemas/Pand",
            oorspronkelijkBouwjaar=2023,
            identificatie=pand_id,
            geometrie=[],
        )
        m.get(
            f"{KADASTER_API_ROOT}panden/{pand_id}",
            json={
                "pand": pand,
                "_links": {"self": {"href": f"{KADASTER_API_ROOT}panden/{pand_id}"}},
            },
        )

        url = furl(reverse("kadaster:adres-pand"))
        url.args["id"] = address_id

        response = self.client.get(url.url)
        hits = len(m.request_history)
        # Expecting 3 requests: location lookup, kadaster adressen, kadaster panden
        # (OAS schema is loaded from local files during testing, not from remote)
        self.assertEqual(hits, 3)

        # Make sure cache gets hit afterwards instead of kadaster
        response = self.client.get(url.url)
        new_hits = len(m.request_history)
        self.assertEqual(hits, new_hits)

    def test_fail_find_pand(self, m):
        # Mock locatie server lookup response
        address_id = "adr-09asnd9as0ndas09dnas09ndsa"
        adresseerbaarobject_id = "9999999999999991"
        lookup_response = {
            "response": {
                "numFound": 1,
                "start": 0,
                "maxScore": 99,
                "docs": [
                    {
                        "bron": "BAG",
                        "woonplaatscode": "9999",
                        "type": "adres",
                        "woonplaatsnaam": "Some-city",
                        "wijkcode": "WK999999",
                        "huis_nlt": "9999",
                        "openbareruimtetype": "Weg",
                        "buurtnaam": "Some-neighborhood",
                        "gemeentecode": "9999",
                        "rdf_seealso": "http://some-bag.nl/bag/id/nummeraanduiding/9999999999999992",
                        "weergavenaam": "Some-street 99, 9999XX Some-city",
                        "straatnaam_verkort": "Some-street",
                        "id": address_id,
                        "gekoppeld_perceel": ["SMC-C-9998", "SMC-C-9999"],
                        "gemeentenaam": "Some-municipality",
                        "buurtcode": "BU99999999",
                        "wijknaam": "Some-wijk 99 Some-city",
                        "identificatie": "9999999999999991-9999999999999992",
                        "openbareruimte_id": "9999999999999993",
                        "waterschapsnaam": "Some-waterschap",
                        "provinciecode": "PV99",
                        "postcode": "9999XX",
                        "provincienaam": "Some-province",
                        "centroide_ll": "POINT(9 9)",
                        "nummeraanduiding_id": "9999999999999992",
                        "waterschapscode": "99",
                        "adresseerbaarobject_id": adresseerbaarobject_id,
                        "huisnummer": 99,
                        "provincieafkorting": "SP",
                        "centroide_rd": "POINT(0 0)",
                        "straatnaam": "Some-street",
                    }
                ],
            }
        }
        m.get(f"{LOCATION_SERVER_ROOT}lookup?id={address_id}", json=lookup_response)

        # mock kadaster api service
        mock_service_oas_get(m, KADASTER_API_ROOT, "kadaster")

        # mock adresseerbaar object from kadaster
        pand_id = "9999999999999994"
        adres = generate_oas_component(
            "kadaster",
            "schemas/Adres",
            adresseerbaarobject_id=adresseerbaarobject_id,
            type="verblijfsobject",
            pandIdentificaties=[pand_id],
        )
        m.get(
            f"{KADASTER_API_ROOT}adressen?adresseerbaarObjectIdentificatie={adresseerbaarobject_id}",
            json={"_embedded": {"adressen": [adres]}},
        )

        bag_error_response = {
            "status": 404,
            "title": "Opgevraagde resource bestaat niet.",
            "code": "notFound",
        }

        m.get(
            f"{KADASTER_API_ROOT}panden/{pand_id}",
            json=bag_error_response,
            status_code=404,
        )
        url = furl(reverse("kadaster:adres-pand"))
        url.args["id"] = address_id

        response = self.client.get(url.url)
        self.assertEqual(response.status_code, 404)
        detail = response.json()["detail"]
        self.assertEqual(
            detail,
            "Opgevraagde resource bestaat niet.",
        )
        title = response.json()["title"]
        self.assertEqual(
            title,
            "Een error heeft plaatsgevonden in een externe API.",
        )

    def test_fail_get_verblijfsobject(self, m):
        # Mock locatie server lookup response
        address_id = "adr-09asnd9as0ndas09dnas09ndsa"
        adresseerbaarobject_id = "9999999999999991"
        lookup_response = {
            "response": {
                "numFound": 1,
                "start": 0,
                "maxScore": 99,
                "docs": [
                    {
                        "bron": "BAG",
                        "woonplaatscode": "9999",
                        "type": "adres",
                        "woonplaatsnaam": "Some-city",
                        "wijkcode": "WK999999",
                        "huis_nlt": "9999",
                        "openbareruimtetype": "Weg",
                        "buurtnaam": "Some-neighborhood",
                        "gemeentecode": "9999",
                        "rdf_seealso": "http://some-bag.nl/bag/id/nummeraanduiding/9999999999999992",
                        "weergavenaam": "Some-street 99, 9999XX Some-city",
                        "straatnaam_verkort": "Some-street",
                        "id": address_id,
                        "gekoppeld_perceel": ["SMC-C-9998", "SMC-C-9999"],
                        "gemeentenaam": "Some-municipality",
                        "buurtcode": "BU99999999",
                        "wijknaam": "Some-wijk 99 Some-city",
                        "identificatie": "9999999999999991-9999999999999992",
                        "openbareruimte_id": "9999999999999993",
                        "waterschapsnaam": "Some-waterschap",
                        "provinciecode": "PV99",
                        "postcode": "9999XX",
                        "provincienaam": "Some-province",
                        "centroide_ll": "POINT(9 9)",
                        "nummeraanduiding_id": "9999999999999992",
                        "waterschapscode": "99",
                        "adresseerbaarobject_id": adresseerbaarobject_id,
                        "huisnummer": 99,
                        "provincieafkorting": "SP",
                        "centroide_rd": "POINT(0 0)",
                        "straatnaam": "Some-street",
                    }
                ],
            }
        }
        m.get(f"{LOCATION_SERVER_ROOT}lookup?id={address_id}", json=lookup_response)

        # mock kadaster api service
        mock_service_oas_get(m, KADASTER_API_ROOT, "kadaster")

        # mock adresseerbaar object from kadaster
        adresseerbaarobject = generate_oas_component(
            "kadaster",
            "schemas/AdresseerbaarObject",
            adresseerbaarobject_id=adresseerbaarobject_id,
            type="something-that-is-not-verblijfsobject",
        )
        m.get(
            f"{KADASTER_API_ROOT}adresseerbareobjecten/{adresseerbaarobject_id}",
            json=adresseerbaarobject,
        )

        url = furl(reverse("kadaster:adres-verblijfsobject"))
        url.args["id"] = address_id

        response = self.client.get(url.url)
        self.assertEqual(response.status_code, 404)
        detail = response.json()["detail"]
        self.assertEqual(
            detail,
            "verblijfsobject not found for adresseerbaarobject_id 9999999999999991",
        )
