from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _

import requests_mock
from django_camunda.client import get_client
from django_camunda.models import CamundaConfig
from django_camunda.utils import serialize_variable
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import GroupFactory, SuperUserFactory, UserFactory
from zac.core.tests.utils import ClearCachesMixin, mock_parallel
from zac.tests.utils import mock_resource_get

ZAKEN_ROOT = "https://some.zrc.nl/api/v1/"
ZAAK_URL = f"{ZAKEN_ROOT}zaken/a955573e-ce3f-4cf3-8ae0-87853d61f47a"
CAMUNDA_ROOT = "https://some.camunda.nl/"
CAMUNDA_API_PATH = "engine-rest/"
CAMUNDA_URL = f"{CAMUNDA_ROOT}{CAMUNDA_API_PATH}"
CREATE_ZAAK_PROCESS_DEFINITION_KEY = "zaak_aanmaken"


def _get_camunda_client():
    config = CamundaConfig.get_solo()
    config.root_url = CAMUNDA_ROOT
    config.rest_api_path = CAMUNDA_API_PATH
    config.save()
    return get_client()


@patch(
    "zac.camunda.process_instances.get_messages",
    return_value=["Annuleer behandeling", "Advies vragen"],
)
@override_settings(
    CREATE_ZAAK_PROCESS_DEFINITION_KEY=CREATE_ZAAK_PROCESS_DEFINITION_KEY
)
@requests_mock.Mocker()
class ProcessInstanceTests(ClearCachesMixin, APITestCase):
    url = reverse_lazy("fetch-process-instances")

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory.create()
        cls.group = GroupFactory.create()

    def setUp(self) -> None:
        super().setUp()
        self.client.force_authenticate(self.user)
        patchers = [
            patch(
                "zac.camunda.messages.get_client", return_value=_get_camunda_client()
            ),
            patch("django_camunda.bpmn.get_client", return_value=_get_camunda_client()),
            patch("django_camunda.api.get_client", return_value=_get_camunda_client()),
            patch(
                "zac.camunda.process_instances.get_client",
                return_value=_get_camunda_client(),
            ),
            patch(
                "zac.core.camunda.utils.get_client", return_value=_get_camunda_client()
            ),
            patch(
                "zac.camunda.process_instances.parallel", return_value=mock_parallel()
            ),
        ]
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_fetch_process_instances(self, m_messages, m_request):
        process_definition_data = [
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
        process_instance_data = [
            {
                "id": "205eae6b-d26f-11ea-86dc-e22fafe5f405",
                "definitionId": process_definition_data[0]["id"],
                "businessKey": "",
                "caseInstanceId": "",
                "suspended": False,
                "tenantId": "",
            },
            {
                "id": "905abd5f-d26f-11ea-86dc-e22fafe5f405",
                "definitionId": process_definition_data[1]["id"],
                "businessKey": "",
                "caseInstanceId": "",
                "suspended": False,
                "tenantId": "",
            },
            {
                "id": "010fe90d-c122-11ea-a817-b6551116eb32",
                "definitionId": process_definition_data[2]["id"],
                "businessKey": "",
                "caseInstanceId": "",
                "suspended": False,
                "tenantId": "",
            },
        ]
        task_data = [
            [],
            [
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
                    "process_definition_id": "accorderen:8:c76c8200-c766-11ea-86dc-e22fafe5f405",
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
                    "process_definition_id": "accorderen:8:c76c8200-c766-11ea-86dc-e22fafe5f405",
                    "process_instance_id": "905abd5f-d26f-11ea-86dc-e22fafe5f403",
                    "task_definition_key": "Activity_0iwp63g",
                    "case_execution_id": None,
                    "case_instance_id": None,
                    "case_definition_id": None,
                    "suspended": False,
                    "form_key": "zac:doRedirect",
                    "tenant_id": None,
                },
            ],
            [],
        ]
        m_request.get(
            f"{CAMUNDA_URL}process-instance?variables=zaakUrl_eq_{ZAAK_URL}&processDefinitionKeyNotIn={CREATE_ZAAK_PROCESS_DEFINITION_KEY}",
            json=[process_instance_data[0]],
        )
        m_request.get(
            f"{CAMUNDA_URL}process-definition?processDefinitionIdIn={','.join([d['id'] for d in sorted(process_definition_data, key=lambda x: x['id'])])}",
            json=process_definition_data,
        )
        for i, process in enumerate(process_instance_data):
            m_request.get(
                f"{CAMUNDA_URL}process-instance?superProcessInstance={process['id']}",
                json=[process_instance_data[i + 1]] if i < 2 else [],
            )
            m_request.get(
                f"{CAMUNDA_URL}task?processInstanceId={process['id']}",
                json=task_data[i],
            )

        response = self.client.get(
            self.url, {"zaakUrl": ZAAK_URL, "includeBijdragezaak": "true"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            [
                {
                    "id": process_instance_data[0]["id"],
                    "definitionId": process_instance_data[0]["definitionId"],
                    "title": process_definition_data[0]["key"],
                    "messages": ["Annuleer behandeling", "Advies vragen"],
                    "tasks": [],
                    "subProcesses": [
                        {
                            "id": process_instance_data[1]["id"],
                            "definitionId": process_instance_data[1]["definitionId"],
                            "title": process_definition_data[1]["key"],
                            "messages": [],
                            "tasks": [
                                {
                                    "id": task_data[1][0]["id"],
                                    "name": "Accorderen",
                                    "created": "2020-07-30T14:19:06Z",
                                    "hasForm": False,
                                    "assignee": {
                                        "username": self.user.username,
                                        "firstName": self.user.first_name,
                                        "fullName": self.user.get_full_name(),
                                        "lastName": self.user.last_name,
                                        "id": self.user.id,
                                        "isStaff": self.user.is_staff,
                                        "email": self.user.email,
                                        "groups": [],
                                    },
                                    "assigneeType": "user",
                                    "canCancelTask": False,
                                    "formKey": "zac:doRedirect",
                                },
                                {
                                    "id": task_data[1][1]["id"],
                                    "name": "Accorderen",
                                    "created": "2020-07-30T14:19:06Z",
                                    "hasForm": False,
                                    "assignee": {
                                        "name": self.group.name,
                                        "fullName": _("Group") + ": " + self.group.name,
                                        "id": self.group.id,
                                    },
                                    "assigneeType": "group",
                                    "canCancelTask": False,
                                    "formKey": "zac:doRedirect",
                                },
                                {
                                    "id": task_data[1][2]["id"],
                                    "name": "Accorderen",
                                    "created": "2020-07-30T14:19:06Z",
                                    "hasForm": False,
                                    "assignee": "",
                                    "assigneeType": "",
                                    "canCancelTask": False,
                                    "formKey": "zac:doRedirect",
                                },
                            ],
                            "subProcesses": [
                                {
                                    "id": process_instance_data[2]["id"],
                                    "definitionId": process_instance_data[2][
                                        "definitionId"
                                    ],
                                    "title": process_definition_data[2]["key"],
                                    "messages": [],
                                    "tasks": [],
                                    "subProcesses": [],
                                }
                            ],
                        }
                    ],
                }
            ],
        )

    def test_fetch_process_instances_exclude_bijdragezaak(self, m_messages, m_request):
        process_definition_data = [
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
        process_instance_data = [
            {
                "id": "205eae6b-d26f-11ea-86dc-e22fafe5f405",
                "definitionId": process_definition_data[0]["id"],
                "businessKey": "",
                "caseInstanceId": "",
                "suspended": False,
                "tenantId": "",
            },
            {
                "id": "905abd5f-d26f-11ea-86dc-e22fafe5f405",
                "definitionId": process_definition_data[1]["id"],
                "businessKey": "",
                "caseInstanceId": "",
                "suspended": False,
                "tenantId": "",
            },
            {
                "id": "010fe90d-c122-11ea-a817-b6551116eb32",
                "definitionId": process_definition_data[2]["id"],
                "businessKey": "",
                "caseInstanceId": "",
                "suspended": False,
                "tenantId": "",
            },
        ]
        task_data = [
            [],
            [
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
            ],
            [],
        ]
        m_request.get(
            f"{CAMUNDA_URL}process-instance?variables=zaakUrl_eq_{ZAAK_URL}",
            json=[process_instance_data[0]],
        )
        m_request.get(
            f"{CAMUNDA_URL}process-definition?processDefinitionIdIn=Aanvraag_behandelen:8:c76c8200-c766-11ea-86dc-e22fafe5f405,accorderen:8:c76c8200-c766-11ea-86dc-e22fafe5f405",
            json=process_definition_data[0:2],
        )
        m_request.get(
            f"{CAMUNDA_URL}process-instance?superProcessInstance={process_instance_data[0]['id']}&variables=zaakUrl_eq_{ZAAK_URL}",
            json=[process_instance_data[1]],
        )
        m_request.get(
            f"{CAMUNDA_URL}process-instance?superProcessInstance={process_instance_data[1]['id']}&variables=zaakUrl_eq_{ZAAK_URL}",
            json=[],
        )
        m_request.get(
            f"{CAMUNDA_URL}task?processInstanceId={process_instance_data[0]['id']}",
            json=task_data[0],
        )
        m_request.get(
            f"{CAMUNDA_URL}task?processInstanceId={process_instance_data[1]['id']}",
            json=task_data[1],
        )

        response = self.client.get(
            self.url, {"zaakUrl": ZAAK_URL, "includeBijdragezaak": "false"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            [
                {
                    "id": "205eae6b-d26f-11ea-86dc-e22fafe5f405",
                    "definitionId": "Aanvraag_behandelen:8:c76c8200-c766-11ea-86dc-e22fafe5f405",
                    "title": "Aanvraag_behandelen",
                    "subProcesses": [
                        {
                            "id": "905abd5f-d26f-11ea-86dc-e22fafe5f405",
                            "definitionId": "accorderen:8:c76c8200-c766-11ea-86dc-e22fafe5f405",
                            "title": "accorderen",
                            "subProcesses": [],
                            "messages": [],
                            "tasks": [
                                {
                                    "id": "a0555196-d26f-11ea-86dc-e22fafe5f405",
                                    "name": "Accorderen",
                                    "created": "2020-07-30T14:19:06Z",
                                    "hasForm": False,
                                    "assigneeType": "user",
                                    "canCancelTask": False,
                                    "formKey": "zac:doRedirect",
                                    "assignee": {
                                        "id": self.user.pk,
                                        "username": f"{self.user}",
                                        "firstName": "",
                                        "fullName": self.user.get_full_name(),
                                        "lastName": "",
                                        "isStaff": False,
                                        "email": self.user.email,
                                        "groups": [],
                                    },
                                }
                            ],
                        }
                    ],
                    "messages": ["Annuleer behandeling", "Advies vragen"],
                    "tasks": [],
                }
            ],
        )

    def test_fail_fetch_process_instances_no_zaak_url(self, m_messages, m_request):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["invalidParams"],
            [{"code": "required", "name": "zaakUrl", "reason": "Dit veld is vereist."}],
        )

    @override_settings(CREATE_ZAAK_PROCESS_DEFINITION_KEY="some-zaak-creation-process")
    def test_fetch_process_instances_exclude_zaak_creation_process(
        self, m_messages, m_request
    ):
        process_definition_data = [
            {
                "id": f"{key}:8:c76c8200-c766-11ea-86dc-e22fafe5f405",
                "key": key,
                "category": "http://bpmn.io/schema/bpmn",
                "description": None,
                "name": None,
                "version": 8,
                "resource": f"{key}.bpmn",
                "deployment_id": "c76a10fd-c766-11ea-86dc-e22fafe5f405",
                "diagram": None,
                "suspended": False,
                "tenant_id": None,
                "version_tag": None,
                "history_time_to_live": None,
                "startable_in_tasklist": True,
            }
            for key in ["some-zaak-creation-process", "accorderen", "Bezwaar_indienen"]
        ]
        process_instance_data = [
            {
                "id": "205eae6b-d26f-11ea-86dc-e22fafe5f405",
                "definitionId": process_definition_data[0]["id"],
                "businessKey": "",
                "caseInstanceId": "",
                "suspended": False,
                "tenantId": "",
            },
            {
                "id": "905abd5f-d26f-11ea-86dc-e22fafe5f405",
                "definitionId": process_definition_data[1]["id"],
                "businessKey": "",
                "caseInstanceId": "",
                "suspended": False,
                "tenantId": "",
            },
            {
                "id": "010fe90d-c122-11ea-a817-b6551116eb32",
                "definitionId": process_definition_data[2]["id"],
                "businessKey": "",
                "caseInstanceId": "",
                "suspended": False,
                "tenantId": "",
            },
        ]
        m_request.get(
            f"{CAMUNDA_URL}process-instance?variables=zaakUrl_eq_{ZAAK_URL}",
            json=process_instance_data,
        )
        m_request.get(
            f"{CAMUNDA_URL}process-definition?processDefinitionIdIn=some-zaak-creation-process%3A8%3Ac76c8200-c766-11ea-86dc-e22fafe5f405%2Caccorderen%3A8%3Ac76c8200-c766-11ea-86dc-e22fafe5f405%2CBezwaar_indienen%3A8%3Ac76c8200-c766-11ea-86dc-e22fafe5f405",
            json=process_definition_data,
        )
        m_request.get(
            f"{CAMUNDA_URL}process-instance?superProcessInstance={process_instance_data[0]['id']}&variables=zaakUrl_eq_{ZAAK_URL}",
            json=[],
        )
        m_request.get(
            f"{CAMUNDA_URL}process-instance?superProcessInstance={process_instance_data[1]['id']}&variables=zaakUrl_eq_{ZAAK_URL}",
            json=[],
        )
        m_request.get(
            f"{CAMUNDA_URL}process-instance?superProcessInstance={process_instance_data[2]['id']}&variables=zaakUrl_eq_{ZAAK_URL}",
            json=[],
        )
        m_request.get(
            f"{CAMUNDA_URL}task?processInstanceId={process_instance_data[0]['id']}",
            json=[],
        )
        m_request.get(
            f"{CAMUNDA_URL}task?processInstanceId={process_instance_data[1]['id']}",
            json=[],
        )
        m_request.get(
            f"{CAMUNDA_URL}task?processInstanceId={process_instance_data[2]['id']}",
            json=[],
        )

        response = self.client.get(
            self.url, {"zaakUrl": ZAAK_URL, "includeBijdragezaak": "false"}
        )

        # Make sure the some-zaak-creation-process process instance isn't returned.
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            [
                {
                    "id": "905abd5f-d26f-11ea-86dc-e22fafe5f405",
                    "definitionId": "accorderen:8:c76c8200-c766-11ea-86dc-e22fafe5f405",
                    "title": "accorderen",
                    "subProcesses": [],
                    "messages": ["Annuleer behandeling", "Advies vragen"],
                    "tasks": [],
                },
                {
                    "id": "010fe90d-c122-11ea-a817-b6551116eb32",
                    "definitionId": "Bezwaar_indienen:8:c76c8200-c766-11ea-86dc-e22fafe5f405",
                    "title": "Bezwaar_indienen",
                    "subProcesses": [],
                    "messages": ["Annuleer behandeling", "Advies vragen"],
                    "tasks": [],
                },
            ],
        )

    def test_fetch_process_instances_exclude_zaak_creation_process(
        self, m_messages, m_request
    ):
        process_definition_data = [
            {
                "id": f"harvo_behandelen:8:c76c8200-c766-11ea-86dc-e22fafe5f405",
                "key": "harvo_behandelen",
                "category": "http://bpmn.io/schema/bpmn",
                "description": None,
                "name": None,
                "version": 8,
                "resource": f"harvo_behandelen.bpmn",
                "deployment_id": "c76a10fd-c766-11ea-86dc-e22fafe5f405",
                "diagram": None,
                "suspended": False,
                "tenant_id": None,
                "version_tag": None,
                "history_time_to_live": None,
                "startable_in_tasklist": True,
            }
        ]
        process_instance_data = [
            {
                "id": "205eae6b-d26f-11ea-86dc-e22fafe5f405",
                "definitionId": process_definition_data[0]["id"],
                "businessKey": "",
                "caseInstanceId": "",
                "suspended": False,
                "tenantId": "",
            },
        ]
        m_request.get(
            f"{CAMUNDA_URL}process-instance?variables=zaakUrl_eq_{ZAAK_URL}",
            json=process_instance_data,
        )
        m_request.get(
            f"{CAMUNDA_URL}process-definition?processDefinitionIdIn=harvo_behandelen%3A8%3Ac76c8200-c766-11ea-86dc-e22fafe5f405",
            json=process_definition_data,
        )
        m_request.get(
            f"{CAMUNDA_URL}process-instance?superProcessInstance={process_instance_data[0]['id']}&variables=zaakUrl_eq_{ZAAK_URL}",
            json=[],
        )
        m_request.get(
            f"{CAMUNDA_URL}task?processInstanceId={process_instance_data[0]['id']}",
            json=[],
        )

        response = self.client.get(
            self.url, {"zaakUrl": ZAAK_URL, "includeBijdragezaak": "false"}
        )

        # Make sure the _some_secret_message message isn't returned.
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            [
                {
                    "id": "205eae6b-d26f-11ea-86dc-e22fafe5f405",
                    "definitionId": "harvo_behandelen:8:c76c8200-c766-11ea-86dc-e22fafe5f405",
                    "title": "harvo_behandelen",
                    "subProcesses": [],
                    "messages": ["Annuleer behandeling", "Advies vragen"],
                    "tasks": [],
                }
            ],
        )
