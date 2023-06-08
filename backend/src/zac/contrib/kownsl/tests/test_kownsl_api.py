from django.test import TestCase

import jwt
import requests_mock
from zds_client.auth import JWT_ALG
from zgw_consumers.api_models.base import factory
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.models import User
from zac.accounts.tests.factories import UserFactory
from zac.contrib.kownsl.constants import KownslTypes
from zac.contrib.kownsl.tests.utils import (
    ADVICE,
    APPROVAL,
    KOWNSL_ROOT,
    REVIEW_REQUEST,
    ZAAK_URL,
)
from zac.core.tests.utils import ClearCachesMixin
from zgw.models.zrc import Zaak

from ..api import (
    create_review_request,
    get_client,
    get_review_requests,
    lock_review_request,
    retrieve_advices,
    retrieve_approvals,
    update_assigned_users_review_request,
)
from ..data import ReviewRequest
from ..models import KownslConfig


@requests_mock.Mocker()
class KownslAPITests(ClearCachesMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.service = Service.objects.create(
            label="kownsl",
            api_type=APITypes.orc,
            api_root=KOWNSL_ROOT,
            auth_type=AuthTypes.zgw,
            client_id="zac",
            secret="supersecret",
            user_id="zac",
        )

        config = KownslConfig.get_solo()
        config.service = cls.service
        config.save()
        zaak_json = generate_oas_component("zrc", "schemas/Zaak", url=ZAAK_URL)
        cls.zaak = factory(Zaak, zaak_json)
        # Let resolve_assignee get the right users and groups
        UserFactory.create(
            username=REVIEW_REQUEST["assignedUsers"][0]["user_assignees"][0]
        )
        UserFactory.create(
            username=REVIEW_REQUEST["assignedUsers"][1]["user_assignees"][0]
        )

    def test_client(self, m):
        mock_service_oas_get(m, KOWNSL_ROOT, "kownsl")
        client = get_client()
        self.assertIsInstance(client.schema, dict)
        # we're using the ZGW Auth mechanism to pass currently logged-in user information
        self.assertIsNotNone(client.auth)
        self.assertEqual(client.auth.user_id, "zac")
        header = client.auth_header["Authorization"]
        self.assertTrue(header.startswith("Bearer "))

        # inspect the user_id claim
        token = header.split(" ")[1]
        claims = jwt.decode(
            token, algorithms=[JWT_ALG], options={"verify_signature": False}
        )
        self.assertEqual(claims["user_id"], "zac")

        self.assertEqual(len(m.request_history), 1)
        self.assertEqual(m.last_request.url, f"{KOWNSL_ROOT}schema/openapi.yaml?v=3")

    def test_create_review_request(self, m):
        mock_service_oas_get(m, KOWNSL_ROOT, "kownsl")
        m.post(
            f"{KOWNSL_ROOT}api/v1/review-requests",
            json=REVIEW_REQUEST,
            status_code=201,
        )

        user = UserFactory.create(username=REVIEW_REQUEST["requester"]["username"])
        self.assertEqual(User.objects.count(), 3)
        review_request = create_review_request(
            ZAAK_URL,
            user,
            documents=["https://doc.nl/123"],
        )
        self.assertEqual(str(review_request.id), REVIEW_REQUEST["id"])
        self.assertEqual(review_request.for_zaak, ZAAK_URL)
        self.assertTrue(m.last_request.headers["Authorization"].startswith("Bearer "))

    def test_retrieve_advices(self, m):
        mock_service_oas_get(m, KOWNSL_ROOT, "kownsl")
        review_request = factory(ReviewRequest, REVIEW_REQUEST)

        m.get(
            f"{KOWNSL_ROOT}api/v1/review-requests/{review_request.id}/advices",
            json=[ADVICE],
        )
        advices = retrieve_advices(review_request)
        self.assertEqual(len(advices), 1)
        advice = advices[0]
        self.assertEqual(advice.advice, ADVICE["advice"])

    def test_retrieve_approvals(self, m):
        mock_service_oas_get(m, KOWNSL_ROOT, "kownsl")
        review_request = factory(
            ReviewRequest,
            {
                **REVIEW_REQUEST,
                "reviewType": KownslTypes.approval,
                "numAdvices": 0,
                "numApprovals": 1,
            },
        )

        m.get(
            f"{KOWNSL_ROOT}api/v1/review-requests/{review_request.id}/approvals",
            json=[APPROVAL],
        )
        approvals = retrieve_approvals(review_request)
        self.assertEqual(len(approvals), 1)
        approval = approvals[0]
        self.assertEqual(approval.approved, True)
        self.assertEqual(approval.toelichting, APPROVAL["toelichting"])

    def test_get_review_requests(self, m):
        mock_service_oas_get(m, KOWNSL_ROOT, "kownsl")
        m.get(
            f"{KOWNSL_ROOT}api/v1/review-requests?for_zaak={ZAAK_URL}",
            json=[REVIEW_REQUEST],
        )
        review_requests = get_review_requests(self.zaak)
        request = review_requests[0]
        self.assertEqual(str(request.id), REVIEW_REQUEST["id"])
        self.assertEqual(m.last_request.qs["for_zaak"], [ZAAK_URL])

    def test_update_assigned_users_review_request(self, m):
        mock_service_oas_get(m, KOWNSL_ROOT, "kownsl")
        m.patch(
            f"{KOWNSL_ROOT}api/v1/review-requests/{REVIEW_REQUEST['id']}",
            json=REVIEW_REQUEST,
        )
        user = UserFactory.create(username=REVIEW_REQUEST["requester"]["username"])
        review_request = update_assigned_users_review_request(
            REVIEW_REQUEST["id"],
            requester=user,
            data={
                "assigned_users": [
                    {
                        "user_assignees": ["some-user"],
                        "group_assignees": [],
                        "deadline": "2023-04-19",
                        "email_notification": True,
                    }
                ],
                "is_being_reconfigured": True,
            },
        )
        self.assertEqual(str(review_request.id), REVIEW_REQUEST["id"])
        self.assertEqual(
            m.last_request.json(),
            {
                "assigned_users": [
                    {
                        "user_assignees": ["some-user"],
                        "group_assignees": [],
                        "deadline": "2023-04-19",
                        "email_notification": True,
                    }
                ],
                "is_being_reconfigured": True,
            },
        )

        # Check user claim is in headers
        jwt_token = m.last_request.headers["Authorization"].split(" ")[-1]
        client = get_client()
        claims = jwt.decode(
            jwt_token,
            client.auth.secret,
            algorithms=[JWT_ALG],
            options={"verify_signature": False},
        )

        self.assertEqual(claims["user_id"], user.username)

    def test_lock_review_request(self, m):
        mock_service_oas_get(m, KOWNSL_ROOT, "kownsl")
        m.patch(
            f"{KOWNSL_ROOT}api/v1/review-requests/{REVIEW_REQUEST['id']}",
            json=REVIEW_REQUEST,
        )
        review_request = lock_review_request(
            REVIEW_REQUEST["id"], lock_reason="some-reason"
        )
        self.assertEqual(str(review_request.id), REVIEW_REQUEST["id"])
        self.assertEqual(
            m.last_request.json(), {"locked": True, "lock_reason": "some-reason"}
        )
