from copy import deepcopy
from unittest.mock import patch

from django.urls import reverse

import jwt
import requests_mock
from furl import furl
from rest_framework import status
from rest_framework.test import APITestCase
from zds_client.auth import JWT_ALG
from zgw_consumers.api_models.base import factory
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import GroupFactory, UserFactory
from zac.contrib.objects.services import factory_review_request, factory_reviews
from zac.core.tests.utils import ClearCachesMixin
from zac.elasticsearch.documents import InformatieObjectDocument
from zac.tests.utils import mock_resource_get
from zgw.models.zrc import Zaak

from .utils import (
    ADVICE,
    DOCUMENTS_ROOT,
    OBJECTS_ROOT,
    OBJECTTYPES_ROOT,
    REVIEW_REQUEST,
    REVIEWS_ADVICE,
    ZAAK_URL,
    ZAKEN_ROOT,
)


@requests_mock.Mocker()
class ViewTests(ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        Service.objects.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=ZAAK_URL,
            identificatie="ZAAK-2020-0010",
            bronorganisatie="123456782",
        )

        # Let slugrelated user/group field resolve
        cls.user = UserFactory.create(
            username="some-user", first_name="John", last_name="Doe"
        )
        cls.group = GroupFactory.create(name="some-group")
        UserFactory.create(
            username=REVIEW_REQUEST["assignedUsers"][0]["userAssignees"][0]
        )
        UserFactory.create(
            username=REVIEW_REQUEST["assignedUsers"][1]["userAssignees"][0]
        )

    def setUp(self):
        super().setUp()

    def test_fail_create_review_query_param(self, m):

        self.client.force_authenticate(user=self.user)
        url = reverse(
            "kownsl:reviewrequest-review",
            kwargs={"request_uuid": REVIEW_REQUEST["id"]},
        )
        body = {"dummy": "data"}

        response = self.client.post(url, body)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), ["'assignee' query parameter is required."])

    def test_fail_get_review_request_query_param(self, m):
        self.client.force_authenticate(user=self.user)
        url = reverse(
            "kownsl:reviewrequest-review",
            kwargs={"request_uuid": REVIEW_REQUEST["id"]},
        )

        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), ["'assignee' query parameter is required."])

    def test_success_get_review_request(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaak)

        rr = factory_review_request(REVIEW_REQUEST)
        rr.reviews = []
        rr.fetched_reviews = True
        user = UserFactory(username=ADVICE["author"]["username"])
        self.client.force_authenticate(user=user)
        url = reverse(
            "kownsl:reviewrequest-review",
            kwargs={"request_uuid": REVIEW_REQUEST["id"]},
        )
        url = furl(url).set({"assignee": f"user:{user}"})

        with patch(
            "zac.contrib.objects.kownsl.api.views.get_review_request", return_value=rr
        ):
            response = self.client.get(url.url)
        self.assertEqual(response.status_code, 200)

    def test_fail_get_review_already_exists(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaak)

        rr = factory_review_request(REVIEW_REQUEST)
        rr.reviews = factory_reviews(REVIEWS_ADVICE).reviews
        rr.fetched_reviews = True
        user = UserFactory(username=ADVICE["author"]["username"])
        self.client.force_authenticate(user=user)
        url = reverse(
            "kownsl:reviewrequest-review",
            kwargs={"request_uuid": REVIEW_REQUEST["id"]},
        )
        url = furl(url).set({"assignee": f"user:{user}"})

        with patch(
            "zac.contrib.objects.kownsl.api.views.get_review_request", return_value=rr
        ):
            response = self.client.get(url.url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json(),
            {
                "detail": f"Dit verzoek is al afgehandeld door `{user.get_full_name()}` vanuit {self.zaak['identificatie']}."
            },
        )

    def test_success_get_review_already_exists_for_group_but_not_user(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaak)

        rev_req = deepcopy(REVIEW_REQUEST)
        rev_req["userDeadlines"] = {
            f"user:{ADVICE['author']['username']}": "2022-04-14",
            f"group:{self.group}": "2022-04-15",
        }
        rev_req["numAssignedUsers"] = 2
        rev_req["assignedUsers"] = [
            {
                "deadline": "2022-04-14",
                "userAssignees": [
                    {
                        "username": "some-author",
                        "firstName": "Some First",
                        "lastName": "Some Last",
                        "fullName": "Some First Some Last",
                    }
                ],
                "groupAssignees": [],
                "emailNotification": False,
            },
            {
                "deadline": "2022-04-15",
                "userAssignees": [],
                "groupAssignees": [
                    {"name": "some-group", "fullName": "Groep some-group"}
                ],
                "emailNotification": False,
            },
        ]
        rr = factory_review_request(rev_req)

        advice = deepcopy(ADVICE)
        advice["adviceDocuments"] = list()
        advice["group"] = {"name": "some-other-group", "fullName": "groeop some group"}
        reviews_advice = deepcopy(REVIEWS_ADVICE)
        reviews_advice["reviews"] = [advice]

        rr.reviews = factory_reviews(reviews_advice).reviews
        rr.fetched_reviews = True
        user = UserFactory(username=ADVICE["author"]["username"])
        user.groups.add(self.group)

        self.client.force_authenticate(user=user)
        url = reverse(
            "kownsl:reviewrequest-review",
            kwargs={"request_uuid": REVIEW_REQUEST["id"]},
        )
        url = furl(url).set({"assignee": f"group:{self.group}"})

        with patch(
            "zac.contrib.objects.kownsl.api.views.get_review_request", return_value=rr
        ):
            response = self.client.get(url.url)
        self.assertEqual(response.status_code, 200)
