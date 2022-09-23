from unittest.mock import patch

from django.urls import reverse

import jwt
import requests_mock
from furl import furl
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import GroupFactory, UserFactory
from zac.core.tests.utils import ClearCachesMixin
from zgw.models.zrc import Zaak

from ..models import KownslConfig
from .utils import ADVICE, KOWNSL_ROOT, REVIEW_REQUEST, ZAAK_URL, ZAKEN_ROOT


@requests_mock.Mocker()
class ViewTests(ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        cls.service = Service.objects.create(
            label="Kownsl",
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

        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=ZAAK_URL,
            identificatie="ZAAK-2020-0010",
            bronorganisatie="123456782",
        )
        zaak = factory(Zaak, cls.zaak)
        cls.views_get_zaak_patcher = patch(
            "zac.contrib.kownsl.views.get_zaak", return_value=zaak
        )
        cls.permissions_get_zaak_patcher = patch(
            "zac.contrib.kownsl.permissions.get_zaak", return_value=zaak
        )
        cls.user = UserFactory.create(
            username="some-user", first_name="John", last_name="Doe"
        )
        cls.group = GroupFactory.create(name="some-group")

    def setUp(self):
        super().setUp()

        self.views_get_zaak_patcher.start()
        self.addCleanup(self.views_get_zaak_patcher.stop)

        self.permissions_get_zaak_patcher.start()
        self.addCleanup(self.permissions_get_zaak_patcher.stop)

    def test_fail_create_review_query_param(self, m):
        self.client.force_authenticate(user=self.user)
        url = reverse(
            "kownsl:reviewrequest-approval",
            kwargs={"request_uuid": REVIEW_REQUEST["id"]},
        )
        body = {"dummy": "data"}

        response = self.client.post(url, body)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), ["'assignee' query parameter is required."])

    def test_fail_get_review_query_param(self, m):
        self.client.force_authenticate(user=self.user)
        url = reverse(
            "kownsl:reviewrequest-approval",
            kwargs={"request_uuid": REVIEW_REQUEST["id"]},
        )

        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), ["'assignee' query parameter is required."])

    def test_success_get_review(self, m):
        mock_service_oas_get(m, KOWNSL_ROOT, "kownsl")
        m.get(
            f"{KOWNSL_ROOT}api/v1/review-requests/{REVIEW_REQUEST['id']}",
            json=REVIEW_REQUEST,
        )
        m.get(
            f"{KOWNSL_ROOT}api/v1/review-requests/{REVIEW_REQUEST['id']}/advices",
            json=[],
        )
        user = UserFactory(username=ADVICE["author"]["username"])
        self.client.force_authenticate(user=user)
        url = reverse(
            "kownsl:reviewrequest-advice",
            kwargs={"request_uuid": REVIEW_REQUEST["id"]},
        )
        url = furl(url).set({"assignee": f"user:{user}"})

        response = self.client.get(url.url)
        self.assertEqual(response.status_code, 200)

    def test_fail_get_review_already_exists(self, m):
        mock_service_oas_get(m, KOWNSL_ROOT, "kownsl")
        m.get(
            f"{KOWNSL_ROOT}api/v1/review-requests/{REVIEW_REQUEST['id']}",
            json=REVIEW_REQUEST,
        )
        m.get(
            f"{KOWNSL_ROOT}api/v1/review-requests/{REVIEW_REQUEST['id']}/advices",
            json=[ADVICE],
        )
        user = UserFactory(username=ADVICE["author"]["username"])
        self.client.force_authenticate(user=user)
        url = reverse(
            "kownsl:reviewrequest-advice",
            kwargs={"request_uuid": REVIEW_REQUEST["id"]},
        )
        url = furl(url).set({"assignee": f"user:{user}"})

        response = self.client.get(url.url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json(),
            {
                "detail": f"Dit verzoek is al afgehandeld door `{user.get_full_name()}` vanuit {self.zaak['identificatie']}."
            },
        )

    def test_success_get_review_already_exists_for_group_but_not_user(self, m):
        mock_service_oas_get(m, KOWNSL_ROOT, "kownsl")

        rev_req = {
            **REVIEW_REQUEST,
            "userDeadlines": {
                "user:some-author": "2022-04-14",
                f"group:{self.group}": "2022-04-14",
            },
            "numAssignedUsers": 2,
        }
        advice = {**ADVICE, "group": self.group.name}
        m.get(
            f"{KOWNSL_ROOT}api/v1/review-requests/{REVIEW_REQUEST['id']}",
            json=rev_req,
        )
        m.get(
            f"{KOWNSL_ROOT}api/v1/review-requests/{REVIEW_REQUEST['id']}/advices",
            json=[advice],
        )
        user = UserFactory(username=advice["author"]["username"])
        self.client.force_authenticate(user=user)
        url = reverse(
            "kownsl:reviewrequest-advice",
            kwargs={"request_uuid": rev_req["id"]},
        )
        url = furl(url).set({"assignee": f"user:{user}"})

        response = self.client.get(url.url)
        self.assertEqual(response.status_code, 200)

    def test_create_advices_assignee_query_param(self, m):
        mock_service_oas_get(m, KOWNSL_ROOT, "kownsl")
        m.get(
            f"{KOWNSL_ROOT}api/v1/review-requests/{REVIEW_REQUEST['id']}",
            json=REVIEW_REQUEST,
        )
        m.get(
            f"{KOWNSL_ROOT}api/v1/review-requests/{REVIEW_REQUEST['id']}/advices",
            json=[],
        )
        m.post(
            f"{KOWNSL_ROOT}api/v1/review-requests/{REVIEW_REQUEST['id']}/advices",
            json={"ok": "yarp"},
            status_code=201,
        )
        # log in - we need to see the user ID in the auth from ZAC to Kownsl
        self.client.force_authenticate(user=self.user)
        url = reverse(
            "kownsl:reviewrequest-advice",
            kwargs={"request_uuid": REVIEW_REQUEST["id"]},
        )
        url = (
            furl(url)
            .set(
                {"assignee": "group:some-group"},
            )
            .url
        )
        body = {"dummy": "data"}
        user = UserFactory(username=ADVICE["author"]["username"])
        self.client.force_authenticate(user=user)
        response = self.client.post(url, body)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data, {"ok": "yarp"})

        auth_header = m.last_request.headers["Authorization"]
        self.assertTrue(auth_header.startswith("Bearer "))
        token = auth_header.split(" ")[1]
        claims = jwt.decode(token, verify=False)
        self.assertEqual(claims["client_id"], "zac")
        self.assertEqual(claims["user_id"], "some-author")
        self.assertEqual(
            m.last_request.json(), {"dummy": "data", "group": "some-group"}
        )
