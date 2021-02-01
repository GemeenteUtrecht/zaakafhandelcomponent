from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

import requests_mock
from django_camunda.models import CamundaConfig
from rest_framework import status

from zac.accounts.tests.factories import UserFactory

ZAAK_URL = "https://some.zrc.nl/api/v1/zaken/a955573e-ce3f-4cf3-8ae0-87853d61f47a"
CAMUNDA_ROOT = "https://some.camunda.nl/"
CAMUNDA_API_PATH = "engine-rest/"
CAMUNDA_URL = f"{CAMUNDA_ROOT}{CAMUNDA_API_PATH}"


@patch("zac.core.camunda.extract_task_form", return_value=None)
@patch(
    "zac.camunda.processes.get_messages",
    return_value=["Annuleer behandeling", "Advies vragen"],
)
@requests_mock.Mocker()
class ProcessInstanceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        config = CamundaConfig.get_solo()
        config.root_url = CAMUNDA_ROOT
        config.rest_api_path = CAMUNDA_API_PATH
        config.save()

        cls.user = UserFactory.create()

    def setUp(self) -> None:
        super().setUp()
        self.client.force_login(self.user)

    def _setUpMock(self, m):
        self.process_definition_data = [
            {
                "id": f"{key}:8:c76c8200-c766-11ea-86dc-e22fafe5f405",
                "key": key,
                "category": "http://bpmn.io/schema/bpmn",
                "description": None,
                "name": None,
                "version": 8,
                "resource": "accorderen.bpmn",
                "deployment_id": "c76a10fd-c766-11ea-86dc-e22fafe5f405",
                "diagram": None,
                "suspended": False,
                "tenant_id": None,
                "version_tag": None,
                "history_time_to_live": None,
                "startable_in_tasklist": True,
            }
            for key in ["Aanvraag_behandelen", "accorderen", "Bezwaar_indienen"]
        ]
        self.process_instance_data = [
            {
                "id": "205eae6b-d26f-11ea-86dc-e22fafe5f405",
                "definitionId": self.process_definition_data[0]["id"],
                "businessKey": "",
                "caseInstanceId": "",
                "suspended": False,
                "tenantId": "",
            },
            {
                "id": "905abd5f-d26f-11ea-86dc-e22fafe5f405",
                "definitionId": self.process_definition_data[1]["id"],
                "businessKey": "",
                "caseInstanceId": "",
                "suspended": False,
                "tenantId": "",
            },
            {
                "id": "010fe90d-c122-11ea-a817-b6551116eb32",
                "definitionId": self.process_definition_data[2]["id"],
                "businessKey": "",
                "caseInstanceId": "",
                "suspended": False,
                "tenantId": "",
            },
        ]
        self.task_data = [
            [],
            [
                {
                    "id": "a0555196-d26f-11ea-86dc-e22fafe5f405",
                    "name": "Accorderen",
                    "assignee": self.user.username,
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
                }
            ],
            [],
        ]

        m.get(
            f"{CAMUNDA_URL}process-instance?variables=zaakUrl_eq_{ZAAK_URL}",
            json=[self.process_instance_data[0]],
        )
        m.get(
            f"{CAMUNDA_URL}process-definition?processDefinitionIdIn={','.join([d['id'] for d in self.process_definition_data])}",
            json=self.process_definition_data,
        )
        for i, process in enumerate(self.process_instance_data):
            m.get(
                f"{CAMUNDA_URL}process-instance?superProcessInstance={process['id']}",
                json=[self.process_instance_data[i + 1]] if i < 2 else [],
            )
            m.get(
                f"{CAMUNDA_URL}task?processInstanceId={process['id']}",
                json=self.task_data[i],
            )

    def test_fetch_process_instances(self, m_messages, m_task_from, m_request):
        self._setUpMock(m_request)

        url = reverse("fetch-process-instances")

        response = self.client.get(url, {"zaak_url": ZAAK_URL})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        expected_data = [
            {
                "id": self.process_instance_data[0]["id"],
                "definitionId": self.process_instance_data[0]["definitionId"],
                "title": self.process_definition_data[0]["key"],
                "messages": ["Annuleer behandeling", "Advies vragen"],
                "tasks": [],
                "subProcesses": [
                    {
                        "id": self.process_instance_data[1]["id"],
                        "definitionId": self.process_instance_data[1]["definitionId"],
                        "title": self.process_definition_data[1]["key"],
                        "messages": [],
                        "tasks": [
                            {
                                "id": self.task_data[1][0]["id"],
                                "executeUrl": reverse(
                                    "core:zaak-task", args=[self.task_data[1][0]["id"]]
                                ),
                                "name": "Accorderen",
                                "created": "2020-07-30T14:19:06Z",
                                "hasForm": False,
                                "assignee": {
                                    "username": self.user.username,
                                    "firstName": self.user.first_name,
                                    "lastName": self.user.last_name,
                                    "id": self.user.id,
                                },
                            }
                        ],
                        "subProcesses": [
                            {
                                "id": self.process_instance_data[2]["id"],
                                "definitionId": self.process_instance_data[2][
                                    "definitionId"
                                ],
                                "title": self.process_definition_data[2]["key"],
                                "messages": [],
                                "tasks": [],
                                "subProcesses": [],
                            }
                        ],
                    }
                ],
            }
        ]

        self.maxDiff = None
        self.assertEqual(data, expected_data)
