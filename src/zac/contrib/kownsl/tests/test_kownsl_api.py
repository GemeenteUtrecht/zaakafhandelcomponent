import uuid

from django.test import TestCase

import requests_mock
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.zaken import Zaak
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service

from zac.accounts.models import User
from zac.core.tests.utils import ClearCachesMixin
from zac.tests.utils import generate_oas_component, mock_service_oas_get

from ..api import (
    create_review_request,
    get_client,
    get_review_requests,
    retrieve_advice_collection,
)
from ..models import KownslConfig


@requests_mock.Mocker()
class KownslAPITests(ClearCachesMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.service = Service.objects.create(
            label="Kownsl",
            api_type=APITypes.orc,
            api_root="https://kownsl.nl",
            auth_type=AuthTypes.api_key,
            header_key="Authorization",
            header_value="Token foobarbaz",
            oas="https://kownsl.nl/api/v1",
        )

        config = KownslConfig.get_solo()
        config.service = cls.service
        config.save()

    def test_client(self, m):
        mock_service_oas_get(
            m, self.service.api_root, "kownsl", oas_url=self.service.oas
        )

        client = get_client()

        self.assertIsInstance(client.schema, dict)
        self.assertIsNone(client.auth)
        self.assertEqual(client.auth_header, {"Authorization": "Token foobarbaz"})
        self.assertEqual(len(m.request_history), 1)
        self.assertEqual(m.last_request.url, f"{self.service.oas}?v=3")

    def test_create_review_request(self, m):
        mock_service_oas_get(
            m, self.service.api_root, "kownsl", oas_url=self.service.oas
        )

        _uuid = uuid.uuid4()
        response = {
            "id": str(_uuid),
            "for_zaak": "https://zaken.nl/api/v1/zaak/123",
            "review_type": "advice",
            "advice_zaak": "",
            "frontend_url": "",
            "num_advices": 0,
            "num_approvals": 0,
        }
        m.post(
            "https://kownsl.nl/api/v1/review-requests", json=response, status_code=201
        )

        review_request = create_review_request("https://zaken.nl/api/v1/zaak/123")

        self.assertEqual(review_request.id, _uuid)
        self.assertEqual(review_request.for_zaak, "https://zaken.nl/api/v1/zaak/123")
        self.assertEqual(m.last_request.headers["Authorization"], "Token foobarbaz")

    def test_retrieve_advice_collection_empty(self, m):
        mock_service_oas_get(
            m, self.service.api_root, "kownsl", oas_url=self.service.oas
        )
        _zaak = generate_oas_component(
            "zrc", "schemas/Zaak", url="https://zaken.nl/api/v1/zaken/123"
        )
        zaak = factory(Zaak, _zaak)
        m.get("https://kownsl.nl/api/v1/advice-collection", status_code=404)

        advice_collection = retrieve_advice_collection(zaak)

        self.assertIsNone(advice_collection)
        self.assertEqual(
            m.last_request.qs["objecturl"], ["https://zaken.nl/api/v1/zaken/123"],
        )

    def test_retrieve_advice_collection(self, m):
        mock_service_oas_get(
            m, self.service.api_root, "kownsl", oas_url=self.service.oas
        )
        _zaak = generate_oas_component(
            "zrc", "schemas/Zaak", url="https://zaken.nl/api/v1/zaken/123"
        )
        zaak = factory(Zaak, _zaak)
        response = {
            "advice_zaak": "https://zaken.nl/api/v1/zaken/123",
            "for_zaak": "https://zaken.nl/api/v1/zaken/abc",
            "advices": [
                {
                    "created": "2020-06-17T10:21:16Z",
                    "author": {"username": "foo", "first_name": "", "last_name": "",},
                    "advice": "dummy",
                    "documents": [],
                }
            ],
        }
        m.get("https://kownsl.nl/api/v1/advice-collection", json=response)

        advice_collection = retrieve_advice_collection(zaak)

        self.assertIsNotNone(advice_collection)
        self.assertEqual(
            advice_collection.for_zaak, "https://zaken.nl/api/v1/zaken/abc"
        )
        self.assertEqual(advice_collection.advices[0].advice, "dummy")
        # side effect: user created
        advice_collection.advices[0].author.user
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.get().username, "foo")

    def test_get_review_requests(self, m):
        mock_service_oas_get(
            m, self.service.api_root, "kownsl", oas_url=self.service.oas
        )
        _zaak = generate_oas_component(
            "zrc", "schemas/Zaak", url="https://zaken.nl/api/v1/zaken/123"
        )
        zaak = factory(Zaak, _zaak)
        _uuid = uuid.uuid4()
        response = {
            "id": str(_uuid),
            "for_zaak": "https://zaken.nl/api/v1/zaak/123",
            "review_type": "advice",
            "advice_zaak": "",
            "frontend_url": "",
            "num_advices": 0,
            "num_approvals": 0,
        }
        m.get(
            f"https://kownsl.nl/api/v1/review-requests?for_zaak={zaak.url}",
            json=[response],
        )

        review_requests = get_review_requests(zaak)

        request = review_requests[0]
        self.assertEqual(request.id, _uuid)
        self.assertEqual(m.last_request.qs["for_zaak"], [zaak.url])
