"""
Test the responses for dynamic form contexts.

The endpoint tested here provides the task data and context for a given Camunda
user task. When using simple forms built into the process model form, the API
describes these forms.
"""
import uuid
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import requests_mock
from django_camunda.camunda_models import factory
from django_camunda.utils import underscoreize
from rest_framework import status
from rest_framework.reverse import reverse_lazy
from rest_framework.test import APITestCase

from zac.accounts.tests.factories import SuperUserFactory
from zac.core.tests.utils import ClearCachesMixin

from ..data import Task

FILES_DIR = Path(__file__).parent / "files"


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


def mock_bpmn_response(
    m: requests_mock.Mocker, file: Path, definition_id: str = "aProcDefId"
) -> None:
    with open(file, "r") as bpmn:
        response = {
            "id": definition_id,
            "bpmn20Xml": bpmn.read(),
        }
    m.get(
        f"https://camunda.example.com/engine-rest/process-definition/{definition_id}/xml",
        headers={"Content-Type": "application/json"},
        json=response,
    )


class DynamicFormTests(ClearCachesMixin, APITestCase):
    endpoint = reverse_lazy("user-task-data", kwargs={"task_id": TASK_DATA["id"]})

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = SuperUserFactory.create()

    def _get_task(self, **overrides):
        data = underscoreize({**TASK_DATA, **overrides})
        return factory(Task, data)

    def setUp(self):
        super().setUp()

        self.client.force_authenticate(user=self.user)

        patcher = patch("zac.camunda.api.views.get_task")
        self.mock_get_task = patcher.start()
        self.addCleanup(patcher.stop)

    @requests_mock.Mocker()
    def test_empty_form_key_and_form_specified(self, m):
        self.mock_get_task.return_value = self._get_task()
        mock_bpmn_response(m, FILES_DIR / "dynamic-form.bpmn")

        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["form"], "")
        expected_formfields = [
            {
                "inputType": "string",
                "label": "Some label",
                "name": "stringField",
                "value": "aDefaultValue",
            },
            {
                "inputType": "int",
                "label": "intField",
                "name": "intField",
                "value": None,
            },
            {
                "inputType": "boolean",
                "label": "boolField",
                "name": "boolField",
                "value": None,
            },
            {
                "inputType": "date",
                "label": "dateField",
                "name": "dateField",
                "value": None,
            },
            {
                "inputType": "enum",
                "label": "enumField",
                "name": "enumField",
                "value": "first",
                "enum": [
                    ["first", "First"],
                    ["second", "second"],
                ],
            },
            {
                "inputType": "string",
                "label": "snake_case",
                "name": "snake_case",
                "value": None,
            },
        ]
        self.assertEqual(data["context"]["formFields"], expected_formfields)

    @requests_mock.Mocker()
    def test_empty_form_key_and_no_form_specified(self, m):
        self.mock_get_task.return_value = self._get_task()
        mock_bpmn_response(m, FILES_DIR / "no-form.bpmn")

        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["form"], "")
        expected_context = {"formFields": []}
        self.assertEqual(data["context"], expected_context)

    @requests_mock.Mocker()
    def test_unknown_form_key_but_form_defined(self, m):
        form_key = str(uuid.uuid4())
        self.mock_get_task.return_value = self._get_task(formKey=form_key)
        mock_bpmn_response(m, FILES_DIR / "dynamic-form.bpmn")

        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["form"], form_key)
        expected_formfields = [
            {
                "inputType": "string",
                "label": "Some label",
                "name": "stringField",
                "value": "aDefaultValue",
            },
            {
                "inputType": "int",
                "label": "intField",
                "name": "intField",
                "value": None,
            },
            {
                "inputType": "boolean",
                "label": "boolField",
                "name": "boolField",
                "value": None,
            },
            {
                "inputType": "date",
                "label": "dateField",
                "name": "dateField",
                "value": None,
            },
            {
                "inputType": "enum",
                "label": "enumField",
                "name": "enumField",
                "value": "first",
                "enum": [
                    ["first", "First"],
                    ["second", "second"],
                ],
            },
            {
                "inputType": "string",
                "label": "snake_case",
                "name": "snake_case",
                "value": None,
            },
        ]
        self.assertEqual(data["context"]["formFields"], expected_formfields)

    @requests_mock.Mocker()
    def test_submit_form_data_ok(self, m):
        self.mock_get_task.return_value = self._get_task()
        mock_bpmn_response(m, FILES_DIR / "dynamic-form.bpmn")
        data = {
            "stringField": "Some string",
            "intField": 42,
            "boolField": True,
            "dateField": "2021-02-09T00:00Z",
            "enumField": "second",
            "snake_case": "snek",
        }

        with patch("zac.camunda.api.views.complete_task") as mock_complete:
            response = self.client.put(self.endpoint, data)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        mock_complete.assert_called_once_with(
            uuid.UUID("598347ee-62fc-46a2-913a-6e0788bc1b8c"),
            {
                "bptlAppId": "",
                "stringField": "Some string",
                "intField": 42,
                "boolField": True,
                "dateField": datetime.fromisoformat("2021-02-09T00:00:00+00:00"),
                "enumField": "second",
                "snake_case": "snek",
            },
        )

    @requests_mock.Mocker()
    def test_submit_form_data_validation_errors(self, m):
        self.mock_get_task.return_value = self._get_task()
        mock_bpmn_response(m, FILES_DIR / "dynamic-form.bpmn")
        data = {
            "stringField": "",
            "intField": "not-an-int",
            "boolField": "not-a-bool",
            "dateField": "not-a-timestamp",
            "enumField": "third",
            "snake_case": "",
        }

        with patch("zac.camunda.api.views.complete_task") as mock_complete:
            response = self.client.put(self.endpoint, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        response_data = response.json()

        # TOD: swap to invalidParams convention
        for key in data:
            with self.subTest(key=key):
                self.assertIn(key, response_data)

        mock_complete.assert_not_called()
