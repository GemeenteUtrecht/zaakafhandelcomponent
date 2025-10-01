import uuid

from django.test import TestCase
from django.urls import reverse

import requests_mock
from rest_framework.authtoken.models import Token
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import mock_service_oas_get

from zac.core.tests.utils import ClearCachesMixin

from ..models import Subscription
from ..subscriptions import subscribe_all


class SubscribeCommandTests(ClearCachesMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.nrc = Service.objects.create(
            api_root="https://some.nrc.nl/api/v1/", api_type=APITypes.nrc
        )

    @requests_mock.Mocker()
    def test_create_subscription(self, m):
        mock_service_oas_get(m, self.nrc.api_root, "nrc")

        m.post(
            "https://some.nrc.nl/api/v1/abonnement",
            status_code=201,
            json={"url": f"https://some.nrc.nl/api/v1/abonnement/{uuid.uuid4()}"},
        )

        result = subscribe_all("https://zac.example.com")
        # 5 kanalen total (zaaktypen, informatieobjecttypen, zaken, objecten, documenten)
        self.assertEqual(len(result), 5)
        # 1 OAS + 5 POSTs
        self.assertEqual(len(m.request_history), 6)
        self.assertEqual(Subscription.objects.count(), 5)

    @requests_mock.Mocker()
    def test_verify_existing(self, m):
        mock_service_oas_get(m, self.nrc.api_root, "nrc")

        base = "https://zac.example.com"
        callback_path = reverse("notifications:callback")
        expected_callback = f"{base}{callback_path}"

        existing = Subscription.objects.create(
            url=f"https://some.nrc.nl/api/v1/abonnement/{uuid.uuid4()}"
        )

        # Existing subscription already registered for one kanaal
        m.get(
            existing.url,
            json={
                "url": existing.url,
                "callbackUrl": expected_callback,  # UPDATED: use named route
                "auth": "Token dummy",
                "kanalen": [{"naam": "objecten", "filters": {}}],
            },
        )

        # New subscriptions for the remaining kanalen
        m.post(
            "https://some.nrc.nl/api/v1/abonnement",
            status_code=201,
            json={"url": f"https://some.nrc.nl/api/v1/abonnement/{uuid.uuid4()}"},
        )

        result = subscribe_all(base)

        # 5 total; 1 already exists -> 4 created now
        self.assertEqual(len(result), 4)
        # 1 OAS + 1 GET existing + 4 POSTs
        self.assertEqual(len(m.request_history), 6)

        token = Token.objects.get()
        self.assertEqual(
            m.last_request.json(),
            {
                "callbackUrl": expected_callback,  # UPDATED
                "auth": f"Token {token.key}",
                "kanalen": [{"naam": "documenten", "filters": {}}],
            },
        )
        self.assertEqual(Subscription.objects.count(), 5)
