from django.test import TestCase

import requests_mock
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service

from zac.core.tests.utils import ClearCachesMixin
from zac.tests.utils import mock_service_oas_get

from ..api import fetch_natuurlijkpersoon, get_client
from ..models import BRPConfig

BRP_API_ROOT = "https://brp.nl/api/v1/"
PERSOON_URL = f"{BRP_API_ROOT}ingeschrevenpersonen/123456782"


class BrpApiTests(ClearCachesMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.service = Service.objects.create(
            label="BRP",
            api_type=APITypes.orc,
            api_root=BRP_API_ROOT,
            auth_type=AuthTypes.api_key,
            header_key="Authorization",
            header_value="Token foobarbaz",
            oas=f"{BRP_API_ROOT}schema",
        )
        config = BRPConfig.get_solo()
        config.service = cls.service
        config.save()

    def _setUpMock(self, m):
        # generate_oas_component doesn't support allOf objects
        naturlijk_persoon = {
            "burgerservicenummer": "1234536782",
            "geslachtsaanduiding": "man",
            "leeftijd": 34,
            "kiesrecht": {},
            "naam": {},
            "geboorte": {},
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

        self.assertEqual(result.burgerservicenummer, "1234536782")

        headers = m.last_request.headers
        self.assertEqual(headers["Authorization"], "Token foobarbaz")
        self.assertEqual(headers["Content-Type"], "application/hal+json")
        self.assertEqual(headers["Accept"], "application/hal+json")
