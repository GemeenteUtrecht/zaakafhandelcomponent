from unittest.mock import patch

from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

import requests_mock
from django_camunda.client import get_client
from django_camunda.models import CamundaConfig
from rest_framework import status
from rest_framework.test import APITestCase

from zac.accounts.tests.factories import GroupFactory, UserFactory

ZAKEN_ROOT = "https://some.zrc.nl/api/v1/"
ZAAK_URL = f"{ZAKEN_ROOT}zaken/a955573e-ce3f-4cf3-8ae0-87853d61f47a"
CAMUNDA_ROOT = "https://some.camunda.nl/"
CAMUNDA_API_PATH = "engine-rest/"
CAMUNDA_URL = f"{CAMUNDA_ROOT}{CAMUNDA_API_PATH}"


def _get_camunda_client():
    config = CamundaConfig.get_solo()
    config.root_url = CAMUNDA_ROOT
    config.rest_api_path = CAMUNDA_API_PATH
    config.save()
    return get_client()


@requests_mock.Mocker()
class FetchTasksTests(APITestCase):
    url = reverse_lazy("fetch-tasks")

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory.create()
        cls.group = GroupFactory.create()
        cls.patchers = [
            patch(
                "zac.camunda.user_tasks.api.get_client",
                return_value=_get_camunda_client(),
            ),
        ]

    def setUp(self) -> None:
        super().setUp()
        self.client.force_authenticate(self.user)
        for patcher in self.patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_not_logged_in(self, m_request):
        self.client.logout()
        response = self.client.get(self.url, {"zaakUrl": ZAAK_URL})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_fail_fetch_tasks_no_zaak_url(self, m_request):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["invalidParams"],
            [{"code": "required", "name": "zaakUrl", "reason": "Dit veld is vereist."}],
        )

    def test_fetch_tasks(self, m_request):
        task_data = [
            {
                "id": "a0555196-d26f-11ea-86dc-e22fafe5f405",
                "name": "Accorderen",
                "assignee": f"user:{self.user.username}",
                "created": "2020-07-30T14:19:06.000+0000",
                "due": None,
                "follow_up": None,
                "delegation_state": None,
                "description": None,
                "execution_id": "a055518b-d26f-11ea-86dc-e22fafe5f405",
                "owner": None,
                "parent_task_id": None,
                "priority": 50,
                "process_definition_id": "accorderen:8:c76c8200-c766-11ea-86dc-e22fafe5f405",
                "process_instance_id": "905abd5f-d26f-11ea-86dc-e22fafe5f405",
                "task_definition_key": "Activity_0iwp63s",
                "case_execution_id": None,
                "case_instance_id": None,
                "case_definition_id": None,
                "suspended": False,
                "form_key": "zac:doRedirect",
                "tenant_id": None,
            },
            {
                "id": "a0555196-d26f-11ea-86dc-e22fafe5f404",
                "name": "Accorderen",
                "assignee": f"group:{self.group.name}",
                "created": "2020-07-30T14:19:06.000+0000",
                "due": None,
                "follow_up": None,
                "delegation_state": None,
                "description": None,
                "execution_id": "a055518b-d26f-11ea-86dc-e22fafe5f404",
                "owner": None,
                "parent_task_id": None,
                "priority": 50,
                "process_definition_id": "accorderen:8:c76c8200-c766-11ea-86dc-e22fafe5f404",
                "process_instance_id": "905abd5f-d26f-11ea-86dc-e22fafe5f404",
                "task_definition_key": "Activity_0iwp63d",
                "case_execution_id": None,
                "case_instance_id": None,
                "case_definition_id": None,
                "suspended": False,
                "form_key": "zac:doRedirect",
                "tenant_id": None,
            },
            {
                "id": "a0555196-d26f-11ea-86dc-e22fafe5f403",
                "name": "Accorderen",
                "assignee": "",
                "created": "2020-07-30T14:19:06.000+0000",
                "due": None,
                "follow_up": None,
                "delegation_state": None,
                "description": None,
                "execution_id": "a055518b-d26f-11ea-86dc-e22fafe5f403",
                "owner": None,
                "parent_task_id": None,
                "priority": 50,
                "process_definition_id": "accorderen:8:c76c8200-c766-11ea-86dc-e22fafe5f403",
                "process_instance_id": "905abd5f-d26f-11ea-86dc-e22fafe5f403",
                "task_definition_key": "Activity_0iwp63g",
                "case_execution_id": None,
                "case_instance_id": None,
                "case_definition_id": None,
                "suspended": False,
                "form_key": "zac:doRedirect",
                "tenant_id": None,
            },
        ]
        m_request.post(
            f"{CAMUNDA_URL}task",
            json=task_data,
        )

        response = self.client.get(self.url, {"zaakUrl": ZAAK_URL})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            [
                {
                    "id": "a0555196-d26f-11ea-86dc-e22fafe5f405",
                    "name": "Accorderen",
                    "created": "2020-07-30T14:19:06Z",
                    "hasForm": False,
                    "assigneeType": "user",
                    "canCancelTask": False,
                    "formKey": "zac:doRedirect",
                    "assignee": {
                        "id": self.user.id,
                        "username": self.user.username,
                        "firstName": self.user.first_name,
                        "fullName": self.user.get_full_name(),
                        "lastName": self.user.last_name,
                        "isStaff": self.user.is_staff,
                        "email": self.user.email,
                        "groups": [],
                    },
                },
                {
                    "id": "a0555196-d26f-11ea-86dc-e22fafe5f404",
                    "name": "Accorderen",
                    "created": "2020-07-30T14:19:06Z",
                    "hasForm": False,
                    "assigneeType": "group",
                    "canCancelTask": False,
                    "formKey": "zac:doRedirect",
                    "assignee": {
                        "id": self.group.id,
                        "name": self.group.name,
                        "fullName": "Groep: " + self.group.name,
                    },
                },
                {
                    "id": "a0555196-d26f-11ea-86dc-e22fafe5f403",
                    "name": "Accorderen",
                    "created": "2020-07-30T14:19:06Z",
                    "hasForm": False,
                    "assigneeType": "",
                    "canCancelTask": False,
                    "formKey": "zac:doRedirect",
                    "assignee": None,
                },
            ],
        )

    def test_fetch_tasks_no_tasks(self, m_request):
        task_data = []
        m_request.post(
            f"{CAMUNDA_URL}task",
            json=task_data,
        )

        response = self.client.get(self.url, {"zaakUrl": ZAAK_URL})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            [],
        )
