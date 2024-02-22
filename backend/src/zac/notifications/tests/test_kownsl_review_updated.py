from copy import deepcopy
from unittest.mock import patch

from django.core.cache import cache
from django.urls import reverse_lazy

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.constants import APITypes
from zgw_consumers.models import APITypes, Service
from zgw_consumers.test import generate_oas_component

from zac.accounts.tests.factories import UserFactory
from zac.contrib.objects.kownsl.data import ReviewRequest
from zac.contrib.objects.kownsl.tests.factories import (
    ZAKEN_ROOT,
    ReviewRequestFactory,
    ReviewRequestObjectFactory,
    ReviewRequestObjectTypeVersionFactory,
)
from zac.core.models import MetaObjectTypesConfig
from zac.core.tests.utils import ClearCachesMixin
from zac.tests.utils import mock_resource_get

REVIEW_REQUEST_OBJECTTYPE = ReviewRequestObjectTypeVersionFactory()
REVIEW_REQUEST_OBJECT = ReviewRequestObjectFactory()

NOTIFICATION = {
    "kanaal": "objecten",
    "hoofdObject": REVIEW_REQUEST_OBJECT["url"],
    "resource": "object",
    "resourceUrl": REVIEW_REQUEST_OBJECT["url"],
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
        cls.user = UserFactory.create(username="notifs")
        cls.patch_fetch_object = patch(
            "zac.notifications.handlers.fetch_object",
            return_value={
                **REVIEW_REQUEST_OBJECT,
                "type": REVIEW_REQUEST_OBJECTTYPE,
                "stringRepresentation": "",
            },
        )
        confg = MetaObjectTypesConfig.get_solo()
        confg.review_request_objecttype = REVIEW_REQUEST_OBJECTTYPE["url"]
        confg.save()
        cls.review_request = ReviewRequestFactory()
        cls.task_data = deepcopy(TASK_DATA)
        cls.task_data["processInstanceId"] = cls.review_request["metadata"][
            "processInstanceId"
        ]

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)
        self.patch_fetch_object.start()
        self.addCleanup(self.patch_fetch_object.stop)

    @patch(
        "zac.contrib.objects.kownsl.api.views.invalidate_review_requests_cache",
        return_value=None,
    )
    def test_user_task_send_message_locked(self, m, mock_invalidate_cache):
        mock_resource_get(m, REVIEW_REQUEST_OBJECT)
        m.get(
            f"https://camunda.example.com/engine-rest/task?processInstanceId={self.review_request['metadata']['processInstanceId']}&taskDefinitionKey={self.review_request['metadata']['taskDefinitionId']}&assignee=user%3Abob",
            json=[{**self.task_data, "assignee": f"user:bob"}],
        )
        m.post(
            "https://camunda.example.com/engine-rest/message",
        )

        rr = factory(ReviewRequest, self.review_request)
        rr.locked = True
        with patch("zac.notifications.handlers.get_review_request", return_value=rr):
            response = self.client.post(self.endpoint, NOTIFICATION)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(m.last_request.method, "POST")
        self.assertEqual(
            m.last_request.url,
            "https://camunda.example.com/engine-rest/message",
        )

    def test_review_request_updated_clears_cache(self, m):
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        zaak = generate_oas_component(
            "zrc", "schemas/Zaak", url=self.review_request["zaak"]
        )
        mock_resource_get(m, REVIEW_REQUEST_OBJECT)

        m.get(
            f"https://camunda.example.com/engine-rest/task?processInstanceId={self.review_request['metadata']['processInstanceId']}&taskDefinitionKey={self.review_request['metadata']['taskDefinitionId']}&assignee=user%3Abob",
            json=[{**self.task_data, "assignee": f"user:bob"}],
        )
        m.post(
            "https://camunda.example.com/engine-rest/message",
        )

        # Fill cache
        cache.set(f"review_request:detail:{self.review_request['id']}", "hello")
        self.assertTrue(
            cache.has_key(f"review_request:detail:{self.review_request['id']}")
        )

        rr = factory(ReviewRequest, self.review_request)
        with patch("zac.notifications.handlers.get_review_request", return_value=rr):
            response = self.client.post(self.endpoint, NOTIFICATION)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            cache.has_key(f"review_request:detail:{self.review_request['id']}")
        )
