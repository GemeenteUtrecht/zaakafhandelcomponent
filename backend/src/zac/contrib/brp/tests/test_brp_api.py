import json

from django.test import TestCase
from django.urls import reverse

import requests_mock
from rest_framework.test import APIClient, APITestCase
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service
from zgw_consumers.test import mock_service_oas_get

from zac.accounts.models import User
from zac.core.tests.utils import ClearCachesMixin

from ..api import fetch_extrainfo_np, fetch_natuurlijkpersoon, get_client
from ..models import BRPConfig

BRP_API_ROOT = "https://brp.nl/api/v1/"
BSN = "123456782"
PERSOON_URL = f"{BRP_API_ROOT}ingeschrevenpersonen/{BSN}"


def setup_BRP_service():
    service = Service.objects.create(
        label="BRP",
        api_type=APITypes.orc,
        api_root=BRP_API_ROOT,
        auth_type=AuthTypes.api_key,
        header_key="Authorization",
        header_value="Token foobarbaz",
        oas=f"{BRP_API_ROOT}schema",
    )
    config = BRPConfig.get_solo()
    config.service = service
    config.save()
    return service, config


class BrpApiTests(ClearCachesMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.service, config = setup_BRP_service()

    def _setUpMock(self, m):
        # generate_oas_component doesn't support allOf objects
        naturlijk_persoon = {
            "burgerservicenummer": BSN,
            "geslachtsaanduiding": "man",
            "leeftijd": 34,
            "kiesrecht": {},
            "naam": {},
            "geboorte": {
                "datum": {"datum": "31-03-1989"},
                "land": {"omschrijving": "Nederland"},
            },
            "_links": {},
        }
        mock_service_oas_get(m, self.service.api_root, "brp", oas_url=self.service.oas)
        m.get(PERSOON_URL, json=naturlijk_persoon)

    @requests_mock.Mocker()
    def test_client(self, m):
        self._setUpMock(m)

        client = get_client()

        self.assertIsInstance(client.schema, dict)
        self.assertIsNone(client.auth)
        self.assertEqual(client.auth_header, {"Authorization": "Token foobarbaz"})
        self.assertEqual(len(m.request_history), 1)
        self.assertEqual(m.last_request.url, f"{self.service.oas}?v=3")

    @requests_mock.Mocker()
    def test_fetch_naturlijk_persoon(self, m):
        self._setUpMock(m)

        result = fetch_natuurlijkpersoon(PERSOON_URL)

        self.assertEqual(result.burgerservicenummer, BSN)

        headers = m.last_request.headers
        self.assertEqual(headers["Authorization"], "Token foobarbaz")
        self.assertEqual(headers["Content-Type"], "application/hal+json")
        self.assertEqual(headers["Accept"], "application/hal+json")

    @requests_mock.Mocker()
    def test_fetch_extrainfo_np(self, m):
        self._setUpMock(m)

        doelbinding = "test"
        fields = "geboorte.datum,geboorte.land"

        request_kwargs = {
            "headers": {"X-NLX-Request-Subject-Identifier": doelbinding},
            "params": {"fields": "geboorte.datum,geboorte.land"},
        }
        path_kwargs = {"burgerservicenummer": BSN}

        result = fetch_extrainfo_np(
            request_kwargs=request_kwargs,
            **path_kwargs,
        )

        headers = m.last_request.headers
        self.assertEqual(headers["X-NLX-Request-Subject-Identifier"], doelbinding)
        self.assertEqual(result.geboortedatum, "31-03-1989")
        self.assertEqual(result.geboorteland, "Nederland")


class BrpApiViewTests(APITestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="john", email="john.doe@johndoe.nl", password="secret"
        )

        self.client.force_authenticate(user=self.superuser)
        self.base_url = reverse("core:post-betrokkene-info")

    def test_csrf_protect_api_view(self):
        self.client_csrf = APIClient(enforce_csrf_checks=True)
        self.client_csrf.force_authenticate(user=self.superuser)
        response = self.client_csrf.post(
            self.base_url,
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_betrokkene_api_no_query_parameters(self):
        response = self.client.post(
            self.base_url,
            data=json.dumps({}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "burgerservicenummer",
                    "code": "required",
                    "reason": "Dit veld is vereist.",
                },
                {
                    "name": "doelbinding",
                    "code": "required",
                    "reason": "Dit veld is vereist.",
                },
                {
                    "name": "fields",
                    "code": "required",
                    "reason": "Dit veld is vereist.",
                },
            ],
        )

    def test_betrokkene_api_invalid_burgerservicenummer(self):
        response = self.client.post(
            self.base_url,
            data=json.dumps(
                {
                    "burgerservicenummer": "912939",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "burgerservicenummer",
                    "code": "invalid",
                    "reason": "Een BSN heeft 9 cijfers.",
                },
                {
                    "name": "doelbinding",
                    "code": "required",
                    "reason": "Dit veld is vereist.",
                },
                {
                    "name": "fields",
                    "code": "required",
                    "reason": "Dit veld is vereist.",
                },
            ],
        )

    def test_betrokkene_api_no_valid_doelbinding(self):
        response = self.client.post(
            self.base_url,
            data=json.dumps(
                {
                    "burgerservicenummer": BSN,
                    "doelbinding": "",
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "doelbinding",
                    "code": "blank",
                    "reason": "Dit veld mag niet leeg zijn.",
                },
                {
                    "name": "fields",
                    "code": "required",
                    "reason": "Dit veld is vereist.",
                },
            ],
        )

    def test_betrokkene_api_no_fields(self):
        response = self.client.post(
            self.base_url,
            data=json.dumps(
                {
                    "burgerservicenummer": BSN,
                    "doelbinding": "test",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["invalidParams"],
            [{"code": "required", "name": "fields", "reason": "Dit veld is vereist."}],
        )

    def test_betrokkene_api_no_valid_fields(self):
        response = self.client.post(
            self.base_url,
            data=json.dumps(
                {
                    "burgerservicenummer": BSN,
                    "doelbinding": "test",
                    "fields": "test,hello,geboorte,geboorte.datum",
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "fields",
                    "code": "invalid",
                    "reason": "Error: dit veld bevatte: test,hello,geboorte, maar mag alleen een (sub)set zijn van: geboorte.datum, geboorte.land, kinderen, partners, verblijfplaats.",
                }
            ],
        )

    @requests_mock.Mocker()
    def test_betrokkene_api_valid_fields(self, m):
        service, config = setup_BRP_service()
        headers = {"X-NLX-Request-Subject-Identifier": "test"}
        extra_info = {
            "_embedded": {
                "kinderen": [
                    {
                        "naam": {
                            "voorletters": "A.",
                            "geslachtsnaam": "Einstein",
                        },
                        "burgerservicenummer": "999993112",
                        "geboorte": {"datum": {"datum": "14-03-1879"}},
                    }
                ]
            },
            "geboorte": {
                "datum": {"datum": "31-03-1989"},
            },
        }
        mock_service_oas_get(m, BRP_API_ROOT, "brp", oas_url=f"{BRP_API_ROOT}schema")
        m.get(
            PERSOON_URL
            + "?fields=geboorte.datum,kinderen,verblijfplaats&expand=kinderen",
            headers=headers,
            json=extra_info,
        )

        response = self.client.post(
            self.base_url,
            data=json.dumps(
                {
                    "burgerservicenummer": BSN,
                    "doelbinding": "test",
                    "fields": "geboorte.datum,kinderen,verblijfplaats",
                }
            ),
            content_type="application/json",
            headers=headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "geboortedatum": "31-03-1989",
                "geboorteland": None,
                "kinderen": [
                    {
                        "naam": "A. Einstein",
                        "burgerservicenummer": "999993112",
                        "geboortedatum": "14-03-1879",
                    }
                ],
                "verblijfplaats": None,
                "partners": None,
            },
        )
