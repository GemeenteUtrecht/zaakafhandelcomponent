import uuid

from django.test import TestCase

import jwt
import requests_mock
from zgw_consumers.api_models.base import factory
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.models import User
from zac.core.tests.utils import ClearCachesMixin
from zgw.models.zrc import Zaak

from ..api import (
    create_review_request,
    get_client,
    get_review_requests,
    retrieve_advices,
    retrieve_approvals,
)
from ..data import ReviewRequest
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
            auth_type=AuthTypes.zgw,
            client_id="zac",
            secret="supersecret",
            oas="https://kownsl.nl/api/v1",
            user_id="zac",
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
        # we're using the ZGW Auth mechanism to pass currently logged-in user information
        self.assertIsNotNone(client.auth)
        self.assertEqual(client.auth.user_id, "zac")
        header = client.auth_header["Authorization"]
        self.assertTrue(header.startswith("Bearer "))

        # inspect the user_id claim
        token = header.split(" ")[1]
        claims = jwt.decode(token, verify=False)
        self.assertEqual(claims["user_id"], "zac")

        self.assertEqual(len(m.request_history), 1)
        self.assertEqual(m.last_request.url, f"{self.service.oas}?v=3")

    def test_create_review_request(self, m):
        mock_service_oas_get(
            m, self.service.api_root, "kownsl", oas_url=self.service.oas
        )

        _uuid = uuid.uuid4()
        response = {
            "id": str(_uuid),
            "created": "2020-12-16T14:15:22Z",
            "forZaak": "https://zaken.nl/api/v1/zaak/123",
            "reviewType": "advice",
            "documents": ["https://doc.nl/123"],
            "frontendUrl": "",
            "numAdvices": 0,
            "numApprovals": 0,
            "numAssignedUsers": 0,
            "toelichting": "",
        }
        m.post(
            "https://kownsl.nl/api/v1/review-requests", json=response, status_code=201
        )

        review_request = create_review_request(
            "https://zaken.nl/api/v1/zaak/123",
            documents=["https://doc.nl/123"],
        )

        self.assertEqual(review_request.id, _uuid)
        self.assertEqual(review_request.for_zaak, "https://zaken.nl/api/v1/zaak/123")
        self.assertTrue(m.last_request.headers["Authorization"].startswith("Bearer "))

    def test_retrieve_advices(self, m):
        # can't use generate_oas_component because Kownsl API schema doesn't have components
        _review_request = {
            "id": "45638aa6-e177-46cc-b580-43339795d5b5",
            "created": "2020-12-16T14:15:22Z",
            "forZaak": "https://zaken.nl/api/v1/zaak/123",
            "reviewType": "advice",
            "documents": [],
            "frontendUrl": f"https://kownsl.nl/45638aa6-e177-46cc-b580-43339795d5b5",
            "numAdvices": 1,
            "numApprovals": 0,
            "numAssignedUsers": 1,
            "toelichting": "Longing for the past but dreading the future",
        }
        review_request = factory(ReviewRequest, _review_request)
        response = [
            {
                "created": "2020-06-17T10:21:16Z",
                "author": {
                    "username": "foo",
                    "firstName": "",
                    "lastName": "",
                },
                "advice": "dummy",
                "documents": [],
            }
        ]
        mock_service_oas_get(
            m, self.service.api_root, "kownsl", oas_url=self.service.oas
        )
        m.get(
            f"https://kownsl.nl/api/v1/review-requests/{review_request.id}/advices",
            json=response,
        )

        advices = retrieve_advices(review_request)

        self.assertEqual(len(advices), 1)

        advice = advices[0]

        self.assertEqual(advice.advice, "dummy")
        self.assertEqual(User.objects.count(), 0)

        # side effect: user created
        advice.author.user
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.get().username, "foo")

    def test_retrieve_approvals(self, m):
        _review_request = {
            "id": "45638aa6-e177-46cc-b580-43339795d5b5",
            "created": "2020-12-16T14:15:22Z",
            "forZaak": "https://zaken.nl/api/v1/zaak/123",
            "reviewType": "approval",
            "documents": [],
            "frontendUrl": f"https://kownsl.nl/45638aa6-e177-46cc-b580-43339795d5b5",
            "numAdvices": 0,
            "numApprovals": 1,
            "numAssignedUsers": 1,
            "toelichting": "Are a thousand tears worth a single smile?",
        }
        review_request = factory(ReviewRequest, _review_request)
        response = [
            {
                "created": "2020-06-17T10:21:16Z",
                "author": {
                    "username": "foo",
                    "firstName": "",
                    "lastName": "",
                },
                "approved": True,
                "toelichting": "When you give an inch, will they take a mile?",
            }
        ]
        mock_service_oas_get(
            m, self.service.api_root, "kownsl", oas_url=self.service.oas
        )
        m.get(
            f"https://kownsl.nl/api/v1/review-requests/{review_request.id}/approvals",
            json=response,
        )

        approvals = retrieve_approvals(review_request)

        self.assertEqual(len(approvals), 1)

        approval = approvals[0]

        self.assertEqual(approval.approved, True)
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(
            approval.toelichting, "When you give an inch, will they take a mile?"
        )

        # side effect: user created
        approval.author.user
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
            "created": "2020-12-16T14:15:22Z",
            "forZaak": "https://zaken.nl/api/v1/zaak/123",
            "reviewType": "advice",
            "documents": [],
            "frontendUrl": "",
            "numAdvices": 0,
            "numApprovals": 0,
            "numAssignedUsers": 0,
            "toelichting": "",
        }
        m.get(
            f"https://kownsl.nl/api/v1/review-requests?for_zaak={zaak.url}",
            json=[response],
        )

        review_requests = get_review_requests(zaak)

        request = review_requests[0]
        self.assertEqual(request.id, _uuid)
        self.assertEqual(m.last_request.qs["for_zaak"], [zaak.url])
