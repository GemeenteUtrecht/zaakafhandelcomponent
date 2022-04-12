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
    "actie": "reviewLocked",
    "aanmaakdatum": "2020-11-04T15:24:00+00:00",
    "kenmerken": {},
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


@requests_mock.Mocker()
class ReviewLockedTests(APITestCase):
    """
    Test the correct behaviour when reviews are locked.
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

    def test_user_task_send_message(self, m):
        mock_service_oas_get(m, "https://kownsl.example.com/api/v1/", "kownsl")
        m.get(
            "https://kownsl.example.com/api/v1/review-requests/74480ee9-0b9c-4392-a96c-47a675552f97",
            json=REVIEW_REQUEST,
        )
        m.get(
            "https://camunda.example.com/engine-rest/task"
            "?processInstanceId=fa962a23-ff20-4184-ba98-b390f2407353&taskDefinitionKey=Activity_e56r7y&assignee=user%3Abob",
            json=[{"id": "some-task-id"}],
        )
        m.post(
            "https://camunda.example.com/engine-rest/message",
        )

        response = self.client.post(self.endpoint, NOTIFICATION)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.assertEqual(m.last_request.method, "POST")
        self.assertEqual(
            m.last_request.url,
            "https://camunda.example.com/engine-rest/message",
        )
