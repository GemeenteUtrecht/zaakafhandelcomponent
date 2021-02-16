from unittest.mock import patch

from django.urls import reverse

import jwt
import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import UserFactory
from zac.core.tests.utils import ClearCachesMixin
from zgw.models.zrc import Zaak

from ..models import KownslConfig

# can't use generate_oas_component because Kownsl API schema doesn't have components
REVIEW_REQUEST = {
    "created": "2020-12-16T14:15:22Z",
    "id": "45638aa6-e177-46cc-b580-43339795d5b5",
    "for_zaak": "https://zaken.nl/api/v1/zaak/123",
    "review_type": "advice",
    "documents": [],
    "frontend_url": f"https://kownsl.nl/45638aa6-e177-46cc-b580-43339795d5b5",
    "num_advices": 1,
    "num_approvals": 0,
    "num_assigned_users": 1,
    "toelichting": "Longing for the past but dreading the future",
    "user_deadlines": {
        "some-user": "2020-12-20",
    },
    "requester": "other-user",
    "metadata": {},
    "zaak_documents": [],
    "reviews": [],
}
ZAKEN_ROOT = "http://zaken.nl/api/v1/"


@requests_mock.Mocker()
class ViewTests(ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        cls.service = Service.objects.create(
            label="Kownsl",
            api_type=APITypes.orc,
            api_root="https://kownsl.nl",
            auth_type=AuthTypes.zgw,
            client_id="zac",
            secret="supersecret",
            oas="https://kownsl.nl/api/v1",
            user_id="zac",
        )

        config = KownslConfig.get_solo()
        config.service = cls.service
        config.save()

        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            identificatie="ZAAK-2020-0010",
            bronorganisatie="123456782",
        )

        zaak = factory(Zaak, cls.zaak)
        cls.get_zaak_patcher = patch(
            "zac.contrib.kownsl.views.get_zaak", return_value=zaak
        )

        cls.user = UserFactory.create(username="some-user")

    def setUp(self):
        super().setUp()

        self.get_zaak_patcher.start()
        self.addCleanup(self.get_zaak_patcher.stop)

    def _mock_oas_get(self, m):
        mock_service_oas_get(
            m, self.service.api_root, "kownsl", oas_url=self.service.oas
        )

    def test_create_approval(self, m):
        self._mock_oas_get(m)
        m.get(
            "https://kownsl.nl/api/v1/review-requests/45638aa6-e177-46cc-b580-43339795d5b5",
            json=REVIEW_REQUEST,
        )
        m.post(
            "https://kownsl.nl/api/v1/review-requests/45638aa6-e177-46cc-b580-43339795d5b5/approvals",
            json={"ok": "yarp"},
            status_code=201,
        )
        # log in - we need to see the user ID in the auth from ZAC to Kownsl
        self.client.force_authenticate(user=self.user)
        url = reverse(
            "kownsl:reviewrequest-approval",
            kwargs={"request_uuid": "45638aa6-e177-46cc-b580-43339795d5b5"},
        )
        body = {"dummy": "data"}

        response = self.client.post(url, body)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, {"ok": "yarp"})

        auth_header = m.last_request.headers["Authorization"]
        self.assertTrue(auth_header.startswith("Bearer "))
        token = auth_header.split(" ")[1]
        claims = jwt.decode(token, verify=False)
        self.assertEqual(claims["client_id"], "zac")
        self.assertEqual(claims["user_id"], "some-user")

    def test_retrieve_review_request_kownsl_not_submitted(self, m):
        self._mock_oas_get(m)

        cases = (
            ("other-user", "false"),
            ("some-user", "true"),
        )

        for username, submitted in cases:
            with self.subTest(username=username, submitted=submitted):
                m.get(
                    "https://kownsl.nl/api/v1/review-requests/45638aa6-e177-46cc-b580-43339795d5b5",
                    json={
                        **REVIEW_REQUEST,
                        "reviews": [{"author": {"username": username}}],
                    },
                )
                self.client.force_authenticate(user=self.user)
                url = reverse(
                    "kownsl:reviewrequest-approval",
                    kwargs={"request_uuid": "45638aa6-e177-46cc-b580-43339795d5b5"},
                )

                response = self.client.get(url)

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response["X-Kownsl-Submitted"], submitted)
