from django.urls import reverse

import requests_mock
from rest_framework.test import APITestCase
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import ApplicationTokenFactory
from zac.core.tests.utils import ClearCachesMixin
from zac.tests.utils import mock_resource_get

ZAKEN_ROOT = "http://zaken.nl/api/v1/"


@requests_mock.Mocker()
class FetchZaakDetailURLResponseTests(ClearCachesMixin, APITestCase):
    """
    Test the API response body for fetch-zaak-detail-url endpoint.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            identificatie="ZAAK-2020-0010",
            bronorganisatie="123456782",
        )
        cls.endpoint = reverse("fetch-zaak-detail-url")
        cls.token = ApplicationTokenFactory.create()
        cls.headers = {"HTTP_AUTHORIZATION": f"ApplicationToken {cls.token.token}"}

    def test_missing_query_parameter(self, m):
        response = self.client.get(self.endpoint, **self.headers)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), ["`zaak` query parameter is required."])

    def test_zaak_does_not_exist(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        m.get(self.zaak["url"], text="Not Found", status_code=404)
        response = self.client.get(
            self.endpoint + f"?zaak={self.zaak['url']}", **self.headers
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            [f"Zaak with `URL`: `{self.zaak['url']}` can not be found."],
        )

    def test_zaak_exists(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaak)
        response = self.client.get(
            self.endpoint + f"?zaak={self.zaak['url']}", **self.headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"zaakDetailUrl": "http://testserver/ui/zaken/123456782/ZAAK-2020-0010"},
        )


@requests_mock.Mocker()
class FetchZaakDetailURLPermissionTests(ClearCachesMixin, APITestCase):
    """
    Test the API permissions for fetch-zaak-detail-url endpoint.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            identificatie="ZAAK-2020-0010",
            bronorganisatie="123456782",
        )
        cls.endpoint = reverse("fetch-zaak-detail-url")
        cls.token = ApplicationTokenFactory.create()
        cls.headers = {"HTTP_AUTHORIZATION": f"ApplicationToken {cls.token.token}"}

    def test_no_token_in_header(self, m):
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json(), {"detail": "Authenticatiegegevens zijn niet opgegeven."}
        )

    def test_wrong_http_authorization_format_in_header(self, m):
        response = self.client.get(self.endpoint, HTTP_AUTHORIZATION="Token something")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json(), {"detail": "Authenticatiegegevens zijn niet opgegeven."}
        )

    def test_correct_token_but_with_error_in_header(self, m):
        response = self.client.get(
            self.endpoint, HTTP_AUTHORIZATION="ApplicationToken 12341212"
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"detail": "Ongeldige token."})

    def test_correct_token(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaak)

        response = self.client.get(
            self.endpoint + f"?zaak={self.zaak['url']}", **self.headers
        )
        self.assertEqual(response.status_code, 200)
