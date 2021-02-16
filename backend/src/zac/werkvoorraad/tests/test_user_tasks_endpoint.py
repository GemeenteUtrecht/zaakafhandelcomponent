from unittest.mock import patch

from django.urls import reverse

from django_camunda.utils import underscoreize
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory

from zac.accounts.tests.factories import UserFactory
from zac.camunda.data import Task

# Taken from https://docs.camunda.org/manual/7.13/reference/rest/task/get/
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


def _get_task(**overrides):
    data = underscoreize({**TASK_DATA, **overrides})
    return factory(Task, data)


class UserTasksTests(APITestCase):
    """
    Test the adhoc activities API endpoint.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = UserFactory.create()
        cls.endpoint = reverse(
            "werkvoorraad:user-tasks",
        )

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    def test_other_user_logging_in(self):
        # Sanity check
        self.client.logout()
        user = UserFactory.create()
        self.client.force_authenticate(user=user)
        with patch(
            "zac.werkvoorraad.views.get_camunda_user_tasks",
            return_value=[],
        ):
            response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_user_tasks_endpoint(self):
        # Sanity check
        with patch(
            "zac.werkvoorraad.views.get_camunda_user_tasks",
            return_value=[_get_task(**{"assignee": self.user})],
        ):
            response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(
            sorted(["assignee", "created", "executeUrl", "hasForm", "id", "name"]),
            sorted(list(data[0].keys())),
        )
