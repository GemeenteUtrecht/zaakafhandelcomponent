from unittest.mock import patch

from django.urls import reverse

import jwt
import requests_mock
from django_camunda.utils import underscoreize
from furl import furl
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import GroupFactory, UserFactory
from zac.camunda.data import Task
from zac.core.tests.utils import ClearCachesMixin
from zgw.models.zrc import Zaak

from ..models import KownslConfig

# can't use generate_oas_component because Kownsl API schema doesn't have components
REVIEW_REQUEST = {
    "created": "2020-12-16T14:15:22Z",
    "id": "45638aa6-e177-46cc-b580-43339795d5b5",
    "forZaak": "https://zaken.nl/api/v1/zaak/123",
    "reviewType": "approval",
    "documents": [],
    "frontend_url": f"https://kownsl.nl/45638aa6-e177-46cc-b580-43339795d5b5",
    "numAdvices": 1,
    "numApprovals": 0,
    "numAssignedUsers": 1,
    "toelichting": "Longing for the past but dreading the future",
    "userDeadlines": {
        "user:some-user": "2020-12-20",
    },
    "requester": {
        "username": "some-other-user",
        "firstName": "",
        "lastName": "",
        "fullName": "",
    },
    "metadata": {},
    "zaakDocuments": [],
    "reviews": [],
    "locked": False,
    "lockReason": "",
}
ZAKEN_ROOT = "http://zaken.nl/api/v1/"


# Taken from https://docs.camunda.org/manual/7.13/reference/rest/task/get/
TASK_DATA = {
    "id": "45638aa6-e177-46cc-b580-43339795d5c6",
    "name": "aName",
    "assignee": None,
    "created": "2013-01-23T13:42:42.000+0200",
    "due": "2013-01-23T13:49:42.576+0200",
    "followUp": "2013-01-23T13:44:42.437+0200",
    "delegationState": "RESOLVED",
    "description": "aDescription",
    "executionId": "anExecution",
    "owner": "anOwner",
    "parentTaskId": None,
    "priority": 42,
    "processDefinitionId": "aProcDefId",
    "processInstanceId": "87a88170-8d5c-4dec-8ee2-972a0be1b564",
    "caseDefinitionId": "aCaseDefId",
    "caseInstanceId": "aCaseInstId",
    "caseExecutionId": "aCaseExecution",
    "taskDefinitionKey": "aTaskDefinitionKey",
    "suspended": False,
    "formKey": "",
    "tenantId": "aTenantId",
}


def _get_task(**overrides):
    data = underscoreize({**TASK_DATA, **overrides})
    return factory(Task, data)


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

    def _mock_oas_get(self, m):
        mock_service_oas_get(
            m, self.service.api_root, "kownsl", oas_url=self.service.oas
        )

    def test_fail_create_review_query_param(self, m):
        self.client.force_authenticate(user=self.user)
        url = reverse(
            "kownsl:reviewrequest-approval",
            kwargs={"request_uuid": "45638aa6-e177-46cc-b580-43339795d5b5"},
        )
        body = {"dummy": "data"}

        response = self.client.post(url, body)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), ["'assignee' query parameter is required."])

    def test_fail_get_review_query_param(self, m):
        self.client.force_authenticate(user=self.user)
        url = reverse(
            "kownsl:reviewrequest-approval",
            kwargs={"request_uuid": "45638aa6-e177-46cc-b580-43339795d5b5"},
        )

        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), ["'assignee' query parameter is required."])

    def test_success_get_review(self, m):
        self._mock_oas_get(m)
        m.get(
            "https://kownsl.nl/api/v1/review-requests/45638aa6-e177-46cc-b580-43339795d5b5",
            json=REVIEW_REQUEST,
        )
        m.get(
            "https://kownsl.nl/api/v1/review-requests/45638aa6-e177-46cc-b580-43339795d5b5/approvals",
            json=[],
        )
        self.client.force_authenticate(user=self.user)
        url = reverse(
            "kownsl:reviewrequest-approval",
            kwargs={"request_uuid": "45638aa6-e177-46cc-b580-43339795d5b5"},
        )
        url = furl(url).set({"assignee": f"user:{self.user}"})

        response = self.client.get(url.url)
        self.assertEqual(response.status_code, 200)

    def test_fail_get_review_already_exists(self, m):
        self._mock_oas_get(m)
        m.get(
            "https://kownsl.nl/api/v1/review-requests/45638aa6-e177-46cc-b580-43339795d5b5",
            json=REVIEW_REQUEST,
        )
        m.get(
            "https://kownsl.nl/api/v1/review-requests/45638aa6-e177-46cc-b580-43339795d5b5/approvals",
            json=[
                {
                    "created": "2020-12-16T14:15:22Z",
                    "author": {
                        "username": self.user.username,
                        "first_name": self.user.first_name,
                        "last_name": self.user.last_name,
                        "full_name": "",
                    },
                    "approved": True,
                    "group": "",
                    "toelichting": "",
                }
            ],
        )
        self.client.force_authenticate(user=self.user)
        url = reverse(
            "kownsl:reviewrequest-approval",
            kwargs={"request_uuid": "45638aa6-e177-46cc-b580-43339795d5b5"},
        )
        url = furl(url).set({"assignee": f"user:{self.user}"})

        response = self.client.get(url.url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json(),
            {
                "detail": f"Dit verzoek is al afgehandeld door {self.user.get_full_name()} vanuit ZAAK {self.zaak['identificatie']}."
            },
        )

    def test_create_approval_assignee_query_param(self, m):
        self._mock_oas_get(m)
        m.get(
            "https://kownsl.nl/api/v1/review-requests/45638aa6-e177-46cc-b580-43339795d5b5",
            json=REVIEW_REQUEST,
        )
        m.get(
            "https://kownsl.nl/api/v1/review-requests/45638aa6-e177-46cc-b580-43339795d5b5/approvals",
            json=[],
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
        url = (
            furl(url)
            .set(
                {"assignee": "group:some-group"},
            )
            .url
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
        self.assertEqual(
            m.last_request.json(), {"dummy": "data", "group": "some-group"}
        )
