from unittest.mock import patch

from django.urls import reverse_lazy

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.models import APITypes, Service
from zgw_consumers.test import mock_service_oas_get

from zac.accounts.models import User

NOTIFICATION = {
    "kanaal": "kownsl",
    "hoofdObject": "https://kownsl.example.com/api/v1/review-requests/74480ee9-0b9c-4392-a96c-47a675552f97",
    "resource": "reviewRequest",
    "resourceUrl": "https://kownsl.example.com/api/v1/review-requests/74480ee9-0b9c-4392-a96c-47a675552f97",
    "actie": "reviewSubmitted",
    "aanmaakdatum": "2020-11-04T15:24:00+00:00",
    "kenmerken": {"author": "bob", "group": ""},
}

REVIEW_REQUEST = {
    "id": "497f6eca-6276-4993-bfeb-53cbbbba6f08",
    "forZaak": "http://example.com",
    "reviewType": "advice",
    "documents": [],
    "frontendUrl": "string",
    "numAdvices": 1,
    "numApprovals": 0,
    "numAssignedUsers": 2,
    "toelichting": "https://kownsl.example.com/497f6eca-6276-4993-bfeb-53cbbbba6f08",
    "userDeadlines": {"user:bob": "2020-11-05"},
    "requester": {
        "username": "alice",
        "firstName": "",
        "lastName": "",
        "fullName": "",
    },
    "metadata": {
        "processInstanceId": "fa962a23-ff20-4184-ba98-b390f2407353",
        "taskDefinitionId": "Activity_e56r7y",
    },
    "locked": False,
    "lockReason": "",
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
    "processInstanceId": "87a88170-8d5c-4dec-8ee2-972a0be1b564",
    "caseDefinitionId": "aCaseDefId",
    "caseInstanceId": "aCaseInstId",
    "caseExecutionId": "aCaseExecution",
    "taskDefinitionKey": "aTaskDefinitionKey",
    "suspended": False,
    "formKey": "",
    "tenantId": "aTenantId",
}


@requests_mock.Mocker()
class ReviewSubmittedTests(APITestCase):
    """
    Test the correct behaviour when reviews are submitted.
    """

    endpoint = reverse_lazy("notifications:kownsl-callback")

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username="notifs")
        cls.kownsl = Service.objects.create(
            api_root="https://kownsl.example.com/api/v1/",
            api_type=APITypes.orc,
        )

    def setUp(self):
        super().setUp()

        self.client.force_authenticate(user=self.user)

    def test_user_task_closed(self, m):
        mock_service_oas_get(m, "https://kownsl.example.com/api/v1/", "kownsl")
        m.get(
            "https://kownsl.example.com/api/v1/review-requests/74480ee9-0b9c-4392-a96c-47a675552f97",
            json=REVIEW_REQUEST,
        )
        m.get(
            "https://camunda.example.com/engine-rest/task"
            "?processInstanceId=fa962a23-ff20-4184-ba98-b390f2407353&taskDefinitionKey=Activity_e56r7y&assignee=user%3Abob",
            json=[{**TASK_DATA, "assignee": f"user:bob"}],
        )
        m.post(
            f"https://camunda.example.com/engine-rest/task/{TASK_DATA['id']}/complete",
            json={"variables": {}},
        )

        response = self.client.post(self.endpoint, NOTIFICATION)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(m.last_request.method, "POST")
        self.assertEqual(
            m.last_request.url,
            f"https://camunda.example.com/engine-rest/task/{TASK_DATA['id']}/complete",
        )

    def test_no_user_tasks_found(self, m):
        """
        Assert that the notification is succesfully handled even if the user task is
        already closed.

        This can happen because of the `returnUrl` action.
        """
        mock_service_oas_get(m, "https://kownsl.example.com/api/v1/", "kownsl")
        m.get(
            "https://kownsl.example.com/api/v1/review-requests/74480ee9-0b9c-4392-a96c-47a675552f97",
            json=REVIEW_REQUEST,
        )
        m.get(
            "https://camunda.example.com/engine-rest/task"
            "?processInstanceId=fa962a23-ff20-4184-ba98-b390f2407353&taskDefinitionKey=Activity_e56r7y&assignee=user%3Abob",
            json=[],
        )

        with patch(
            "zac.contrib.kownsl.views.set_assignee_and_complete_task"
        ) as mock_complete:
            response = self.client.post(self.endpoint, NOTIFICATION)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(m.last_request.method, "GET")
        mock_complete.assert_not_called()

    def test_user_task_closed_group_assignee_still_sets_a_user_assignee(self, m):
        mock_service_oas_get(m, "https://kownsl.example.com/api/v1/", "kownsl")
        m.get(
            "https://kownsl.example.com/api/v1/review-requests/74480ee9-0b9c-4392-a96c-47a675552f97",
            json=REVIEW_REQUEST,
        )
        m.get(
            "https://camunda.example.com/engine-rest/task"
            "?processInstanceId=fa962a23-ff20-4184-ba98-b390f2407353&taskDefinitionKey=Activity_e56r7y&assignee=group%3Asome-group",
            json=[
                {
                    **TASK_DATA,
                    "assignee": "group:some-group",
                }
            ],
        )
        m.post(
            f"https://camunda.example.com/engine-rest/task/{TASK_DATA['id']}/assignee",
            status_code=204,
        )
        m.post(
            f"https://camunda.example.com/engine-rest/task/{TASK_DATA['id']}/complete",
            json={"variables": {}},
        )

        response = self.client.post(
            self.endpoint,
            {**NOTIFICATION, "kenmerken": {"author": "bob", "group": "some-group"}},
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(m.last_request.method, "POST")
        self.assertEqual(
            m.last_request.url,
            f"https://camunda.example.com/engine-rest/task/{TASK_DATA['id']}/complete",
        )
