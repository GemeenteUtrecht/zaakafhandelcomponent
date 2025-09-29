from copy import deepcopy
from unittest.mock import patch

from django.core.cache import cache
from django.urls import reverse_lazy

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import UserFactory
from zac.contrib.objects.kownsl.tests.factories import (
    ZAKEN_ROOT,
    review_request_factory,
    review_request_object_factory,
    review_request_object_type_version_factory,
)
from zac.core.models import MetaObjectTypesConfig
from zac.core.tests.utils import ClearCachesMixin
from zac.tests.utils import mock_resource_get

REVIEW_REQUEST_OBJECTTYPE = review_request_object_type_version_factory()
REVIEW_REQUEST_OBJECT = review_request_object_factory()

# UPDATED: snake_case keys
NOTIFICATION = {
    "kanaal": "objecten",
    "hoofd_object": REVIEW_REQUEST_OBJECT["url"],
    "resource": "object",
    "resource_url": REVIEW_REQUEST_OBJECT["url"],
    "actie": "update",
    "aanmaakdatum": "2020-11-04T15:24:00+00:00",
    "kenmerken": {"object_type": REVIEW_REQUEST_OBJECTTYPE["url"]},
}

TASK_DATA = {
    "id": "598347ee-62fc-46a2-913a-6e0788bc1b8c",
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
    "processInstanceId": "",
    "caseDefinitionId": "aCaseDefId",
    "caseInstanceId": "aCaseInstId",
    "caseExecutionId": "aCaseExecution",
    "taskDefinitionKey": "aTaskDefinitionKey",
    "suspended": False,
    "formKey": "",
    "tenantId": "aTenantId",
}


@requests_mock.Mocker()
class ReviewUpdatedTests(ClearCachesMixin, APITestCase):
    """
    Test the correct behaviour when reviews are updated.
    """

    endpoint = reverse_lazy("notifications:callback")

    @classmethod
    def setUpTestData(cls):
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        rr = deepcopy(REVIEW_REQUEST_OBJECT)
        rr["locked"] = True
        cls.user = UserFactory.create(username="notifs")
        confg = MetaObjectTypesConfig.get_solo()
        confg.review_request_objecttype = REVIEW_REQUEST_OBJECTTYPE["url"]
        confg.save()
        cls.review_request = review_request_factory()
        cls.task_data = deepcopy(TASK_DATA)
        cls.task_data["processInstanceId"] = cls.review_request["metadata"][
            "processInstanceId"
        ]
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=REVIEW_REQUEST_OBJECT["record"]["data"]["zaak"],
        )

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    # UPDATED: patch path for invalidate_review_requests_cache
    @patch(
        "zac.contrib.objects.kownsl.cache.invalidate_review_requests_cache",
        return_value=None,
    )
    def test_user_task_send_message_locked(self, m, mock_invalidate_cache):
        mock_service_oas_get(m, ZAKEN_ROOT, "ztc")
        mock_resource_get(m, self.zaak)
        m.get(
            f"https://camunda.example.com/engine-rest/task"
            f"?processInstanceId={self.review_request['metadata']['processInstanceId']}"
            f"&taskDefinitionKey={self.review_request['metadata']['taskDefinitionId']}"
            f"&assignee=user%3Abob",
            json=[{**self.task_data, "assignee": "user:bob"}],
        )
        m.post("https://camunda.example.com/engine-rest/message")

        rr = deepcopy(REVIEW_REQUEST_OBJECT)
        rr["record"]["data"]["locked"] = True
        rr["type"] = REVIEW_REQUEST_OBJECTTYPE
        rr["stringRepresentation"] = ""

        # UPDATED: patch path for fetch_object inside the new handler module
        with patch(
            "zac.notifications.handlers.objecten.fetch_object",
            return_value=rr,
        ):
            response = self.client.post(self.endpoint, NOTIFICATION)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(m.request_history[-1].method, "POST")
        self.assertEqual(
            m.request_history[-1].url,
            "https://camunda.example.com/engine-rest/message",
        )

    def test_review_request_updated_clears_cache(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "ztc")
        mock_resource_get(m, self.zaak)

        m.get(
            f"https://camunda.example.com/engine-rest/task"
            f"?processInstanceId={self.review_request['metadata']['processInstanceId']}"
            f"&taskDefinitionKey={self.review_request['metadata']['taskDefinitionId']}"
            f"&assignee=user%3Abob",
            json=[{**self.task_data, "assignee": "user:bob"}],
        )
        m.post("https://camunda.example.com/engine-rest/message")

        # Fill cache
        cache.set(f"review_request:detail:{self.review_request['id']}", "hello")
        self.assertTrue(
            cache.has_key(f"review_request:detail:{self.review_request['id']}")
        )

        rr = deepcopy(REVIEW_REQUEST_OBJECT)
        rr["type"] = REVIEW_REQUEST_OBJECTTYPE
        rr["stringRepresentation"] = ""

        # UPDATED: patch path for fetch_object inside the new handler module
        with patch(
            "zac.notifications.handlers.objecten.fetch_object",
            return_value=rr,
        ):
            response = self.client.post(self.endpoint, NOTIFICATION)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            cache.has_key(f"review_request:detail:{self.review_request['id']}")
        )
