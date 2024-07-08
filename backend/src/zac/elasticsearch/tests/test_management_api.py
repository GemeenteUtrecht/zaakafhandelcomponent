from unittest.mock import MagicMock, patch

from django.urls import reverse_lazy

import requests_mock
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase, APITransactionTestCase
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import UserFactory
from zac.core.tests.utils import ClearCachesMixin
from zac.tests.utils import mock_resource_get, paginated_response

from .utils import ESMixin

CATALOGI_ROOT = "https://api.catalogi.nl/api/v1/"
ZAKEN_ROOT = "https://api.zaken.nl/api/v1/"
CATALOGUS_URL = f"{CATALOGI_ROOT}catalogi/dfb14eb7-9731-4d22-95c2-dff4f33ef36d"


class IndexElasticsearchAPITests(APITestCase):
    endpoint = reverse_lazy("index-elasticsearch")

    def test_permissions_not_token_authenticated(self):
        response = self.client.post(self.endpoint)
        self.assertEqual(response.status_code, 401)

    def test_permissions_not_staff_user(self):
        user = UserFactory.create(is_staff=False)
        token, created = Token.objects.get_or_create(user=user)
        response = self.client.post(self.endpoint, HTTP_AUTHORIZATION=f"Token {token}")
        self.assertEqual(response.status_code, 403)

    @patch("zac.elasticsearch.management.views.call_command")
    def test_success(self, mock_call_command):
        user = UserFactory.create(is_staff=True)
        token, created = Token.objects.get_or_create(user=user)
        response = self.client.post(
            self.endpoint, {"reset_indices": True}, HTTP_AUTHORIZATION=f"Token {token}"
        )
        self.assertEqual(response.status_code, 204)
        mock_call_command.assert_called_once_with(
            "index_all --chunk-size=100 --max-workers=2"
        )

    def test_invalid(self):
        user = UserFactory.create(is_staff=True)
        token, created = Token.objects.get_or_create(user=user)
        response = self.client.post(self.endpoint, HTTP_AUTHORIZATION=f"Token {token}")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "nonFieldErrors",
                    "code": "invalid",
                    "reason": "Geef 1 van `reindex_last`, `reindex_zaak` of `reset_indices` op.",
                }
            ],
        )

    def test_invalid_reindex_both_last_and_zaak(self):
        user = UserFactory.create(is_staff=True)
        token, created = Token.objects.get_or_create(user=user)
        with patch("zac.elasticsearch.management.serializers.get_zaak"):
            response = self.client.post(
                self.endpoint,
                {"index_last": 100, "index_zaak": "https://somezaak.nl/"},
                HTTP_AUTHORIZATION=f"Token {token}",
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "nonFieldErrors",
                    "code": "invalid",
                    "reason": "Geef 1 van `reindex_last`, `reindex_zaak` of `reset_indices` op.",
                }
            ],
        )

    @patch("zac.elasticsearch.management.views.call_command")
    def test_success_reindex_last(self, mock_call_command):
        user = UserFactory.create(is_staff=True)
        token, created = Token.objects.get_or_create(user=user)
        response = self.client.post(
            self.endpoint, {"reindex_last": 100}, HTTP_AUTHORIZATION=f"Token {token}"
        )
        self.assertEqual(response.status_code, 204)
        mock_call_command.assert_called_once_with(
            "index_all --chunk-size=100 --max-workers=2 --reindex-last=100"
        )

    @patch("zac.elasticsearch.management.views.call_command")
    def test_success_reindex_last_documenten(self, mock_call_command):
        user = UserFactory.create(is_staff=True)
        token, created = Token.objects.get_or_create(user=user)
        response = self.client.post(
            self.endpoint,
            {"reindex_last": 100, "index": "index_documenten"},
            HTTP_AUTHORIZATION=f"Token {token}",
        )
        self.assertEqual(response.status_code, 204)
        mock_call_command.assert_called_once_with(
            "index_documenten --chunk-size=100 --max-workers=2 --reindex-last=100"
        )

    @patch("zac.elasticsearch.management.views.call_command")
    def test_fail_and_success_reindex_zaak(self, mock_call_command):
        user = UserFactory.create(is_staff=True)
        token, created = Token.objects.get_or_create(user=user)
        with self.subTest("Fail at get_zaak"):
            response = self.client.post(
                self.endpoint,
                {"reindex_zaak": "https://some-zaak.nl/"},
                HTTP_AUTHORIZATION=f"Token {token}",
            )
            self.assertEqual(response.status_code, 400)
            self.assertEqual(
                response.json()["invalidParams"],
                [
                    {
                        "name": "reindexZaak",
                        "code": "invalid",
                        "reason": "De service voor de url https://some-zaak.nl/ is niet geconfigureerd in de admin.",
                    }
                ],
            )
        with self.subTest("Success"):
            zaak = MagicMock()
            type(zaak).url = "https://some-zaak.nl/"
            with patch(
                "zac.elasticsearch.management.serializers.get_zaak", return_value=zaak
            ) as mock_zaak:
                response = self.client.post(
                    self.endpoint,
                    {"reindex_zaak": "https://some-zaak.nl/"},
                    HTTP_AUTHORIZATION=f"Token {token}",
                )
                self.assertEqual(response.status_code, 204)
                mock_call_command.assert_called_once_with(
                    "index_all --chunk-size=100 --max-workers=2 --reindex-zaak=https://some-zaak.nl/"
                )
                mock_zaak.assert_called_once()


@requests_mock.Mocker()
class ReIndexZaakElasticsearchAPITests(
    ClearCachesMixin, ESMixin, APITransactionTestCase
):
    catalogus = generate_oas_component(
        "ztc",
        "schemas/Catalogus",
        url=CATALOGUS_URL,
        domein="DOME",
    )
    zaaktype = generate_oas_component(
        "ztc",
        "schemas/ZaakType",
        url=f"{CATALOGI_ROOT}zaaktypen/a8c8bc90-defa-4548-bacd-793874c013aa",
        catalogus=catalogus["url"],
    )
    zaak = generate_oas_component(
        "zrc",
        "schemas/Zaak",
        url=f"{ZAKEN_ROOT}zaken/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
        zaaktype=zaaktype["url"],
        bronorganisatie="002220647",
        identificatie="ZAAK1",
        vertrouwelijkheidaanduiding="zaakvertrouwelijk",
    )
    endpoint = reverse_lazy(
        "reindex-zaak-elasticsearch",
        kwargs={
            "bronorganisatie": zaak["bronorganisatie"],
            "identificatie": zaak["identificatie"],
        },
    )

    def setUp(self):
        super().setUp()
        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)

    def test_permissions_not_token_authenticated(self, m):
        response = self.client.post(self.endpoint)
        self.assertEqual(response.status_code, 401)

    def test_permissions_not_staff_user(self, m):
        user = UserFactory.create(is_staff=False)
        token, created = Token.objects.get_or_create(user=user)
        response = self.client.post(self.endpoint, HTTP_AUTHORIZATION=f"Token {token}")
        self.assertEqual(response.status_code, 403)

    @patch("zac.elasticsearch.management.views.call_command")
    def test_success(self, m, mock_call_command):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")

        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie={self.zaak['bronorganisatie']}&identificatie={self.zaak['identificatie']}",
            json=paginated_response([self.zaak]),
        )
        mock_resource_get(m, self.zaaktype)

        user = UserFactory.create(is_staff=True)
        token, created = Token.objects.get_or_create(user=user)
        response = self.client.post(self.endpoint, HTTP_AUTHORIZATION=f"Token {token}")
        self.assertEqual(response.status_code, 204)
        mock_call_command.assert_called_once_with(
            f"index_all --chunk-size=100 --max-workers=2 --reindex-zaak={self.zaak['url']}"
        )
