from copy import deepcopy
from unittest.mock import patch

from django.urls import reverse

import requests_mock
from furl import furl
from rest_framework.test import APITestCase
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from zac.accounts.tests.factories import GroupFactory, UserFactory
from zac.contrib.objects.services import factory_review_request, factory_reviews
from zac.core.tests.utils import ClearCachesMixin
from zac.tests.compat import generate_oas_component, mock_service_oas_get
from zac.tests.utils import mock_resource_get

from .factories import (
    DOCUMENTS_ROOT,
    ZAAK_URL,
    ZAKEN_ROOT,
    advice_factory,
    review_request_factory,
    reviews_factory,
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
        cls.review_request = review_request_factory()
        cls.advice = advice_factory()
        cls.reviews_advice = reviews_factory()
        cls.group = GroupFactory.create(name="some-group")

    def test_fail_create_review_query_param(self, m):
        self.client.force_authenticate(user=self.user)
        url = reverse(
            "kownsl:reviewrequest-advice",
            kwargs={"request_uuid": self.review_request["id"]},
        )
        body = {"dummy": "data"}

        response = self.client.post(url, body)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "assignee",
                    "code": "required",
                    "reason": "Dit veld is vereist.",
                }
            ],
        )

    def test_fail_get_review_request_query_param(self, m):
        self.client.force_authenticate(user=self.user)
        url = reverse(
            "kownsl:reviewrequest-advice",
            kwargs={"request_uuid": self.review_request["id"]},
        )

        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "assignee",
                    "code": "required",
                    "reason": "Dit veld is vereist.",
                }
            ],
        )

    def test_success_get_review_request(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaak)

        rr = factory_review_request(self.review_request)
        # Avoid patching fetch_reviews and everything
        rr.reviews = []
        rr.fetched_reviews = True

        user = UserFactory(username=self.advice["author"]["username"])
        self.client.force_authenticate(user=user)
        url = reverse(
            "kownsl:reviewrequest-advice",
            kwargs={"request_uuid": self.review_request["id"]},
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

        rr = factory_review_request(self.review_request)
        # Avoid patching fetch_reviews and everything
        rr.reviews = factory_reviews(self.reviews_advice).reviews
        rr.fetched_reviews = True

        user = UserFactory(username=self.advice["author"]["username"])
        self.client.force_authenticate(user=user)
        url = reverse(
            "kownsl:reviewrequest-advice",
            kwargs={"request_uuid": self.review_request["id"]},
        )
        url = furl(url).set({"assignee": f"user:{user}"})

        with patch(
            "zac.contrib.objects.kownsl.api.views.get_review_request", return_value=rr
        ):
            response = self.client.get(url.url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["detail"],
            f"Dit verzoek is al afgehandeld door `{user.get_full_name()}` vanuit {self.zaak['identificatie']}.",
        )

    def test_success_get_review_already_exists_for_group_but_not_user(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaak)

        rev_req = deepcopy(self.review_request)
        rev_req["userDeadlines"] = {
            f"user:{self.advice['author']['username']}": "2022-04-14",
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

        advice = deepcopy(self.advice)
        advice["reviewDocuments"] = list()
        advice["group"] = {"name": "some-other-group", "fullName": "groeop some group"}
        reviews_advice = deepcopy(self.reviews_advice)
        reviews_advice["reviews"] = [advice]

        # Avoid patching fetch_reviews and everything
        rr.reviews = factory_reviews(reviews_advice).reviews
        rr.fetched_reviews = True

        user = UserFactory(username=self.advice["author"]["username"])
        user.groups.add(self.group)

        self.client.force_authenticate(user=user)
        url = reverse(
            "kownsl:reviewrequest-advice",
            kwargs={"request_uuid": self.review_request["id"]},
        )
        url = furl(url).set({"assignee": f"group:{self.group}"})

        with patch(
            "zac.contrib.objects.kownsl.api.views.get_review_request", return_value=rr
        ):
            response = self.client.get(url.url)
        self.assertEqual(response.status_code, 200)
