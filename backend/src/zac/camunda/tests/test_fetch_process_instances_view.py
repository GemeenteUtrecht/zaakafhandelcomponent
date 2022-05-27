from unittest.mock import patch

from django.urls import reverse
from django.utils.translation import gettext_lazy as _

import requests_mock
from django_camunda.models import CamundaConfig
from django_camunda.utils import serialize_variable
from rest_framework import status
from rest_framework.test import APITransactionTestCase
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import GroupFactory, SuperUserFactory, UserFactory
from zac.tests.utils import mock_resource_get

ZAKEN_ROOT = "https://some.zrc.nl/api/v1/"
ZAAK_URL = f"{ZAKEN_ROOT}zaken/a955573e-ce3f-4cf3-8ae0-87853d61f47a"
CAMUNDA_ROOT = "https://some.camunda.nl/"
CAMUNDA_API_PATH = "engine-rest/"
CAMUNDA_URL = f"{CAMUNDA_ROOT}{CAMUNDA_API_PATH}"


@patch("zac.core.camunda.extract_task_form", return_value=None)
@patch(
    "zac.camunda.processes.get_messages",
    return_value=["Annuleer behandeling", "Advies vragen"],
)
@requests_mock.Mocker()
class ProcessInstanceTests(APITransactionTestCase):
    def setUp(self) -> None:
        super().setUp()
        config = CamundaConfig.get_solo()
        config.root_url = CAMUNDA_ROOT
        config.rest_api_path = CAMUNDA_API_PATH
        config.save()

        self.user = UserFactory.create()
        self.group = GroupFactory.create()

        self.client.force_login(self.user)

    def test_fetch_process_instances(self, m_messages, m_task_from, m_request):
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
            ],
            [],
        ]
        m_request.get(
            f"{CAMUNDA_URL}process-instance?variables=zaakUrl_eq_{ZAAK_URL}",
            json=[process_instance_data[0]],
        )
        m_request.get(
            f"{CAMUNDA_URL}process-definition?processDefinitionIdIn={','.join([d['id'] for d in process_definition_data])}",
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

        url = reverse("fetch-process-instances-list")
        response = self.client.get(url, {"zaak_url": ZAAK_URL})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        expected_data = [
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
                            },
                            {
                                "id": task_data[1][2]["id"],
                                "name": "Accorderen",
                                "created": "2020-07-30T14:19:06Z",
                                "hasForm": False,
                                "assignee": "",
                                "assigneeType": "",
                                "canCancelTask": False,
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
        ]

        self.assertEqual(data, expected_data)

    def test_fail_fetch_process_instances_no_zaak_url(
        self, m_messages, m_task_from, m_request
    ):
        url = reverse("fetch-process-instances-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), {"detail": "missing zaak_url"})

    def test_fetch_zaak_url_from_process_instance(
        self, m_messages, m_task_from, m_request
    ):
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        mock_service_oas_get(m_request, ZAKEN_ROOT, "zrc")

        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=ZAAK_URL,
        )
        mock_resource_get(m_request, zaak)

        m_request.get(
            f"{CAMUNDA_URL}process-instance/205eae6b-d26f-11ea-86dc-e22fafe5f405",
            json={
                "id": "205eae6b-d26f-11ea-86dc-e22fafe5f405",
                "definitionId": "Aanvraag_behandelen:8:c76c8200-c766-11ea-86dc-e22fafe5f405",
                "businessKey": "",
                "caseInstanceId": "",
                "suspended": False,
                "tenantId": "",
            },
        )
        m_request.get(
            f"{CAMUNDA_URL}process-instance/205eae6b-d26f-11ea-86dc-e22fafe5f405/variables/zaakUrl?deserializeValue=false",
            json=serialize_variable(ZAAK_URL),
        )
        url = reverse(
            "fetch-process-instances-zaak",
            kwargs={"pk": "205eae6b-d26f-11ea-86dc-e22fafe5f405"},
        )
        superuser = SuperUserFactory.create()
        self.client.force_login(superuser)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "bronorganisatie": zaak["bronorganisatie"],
                "identificatie": zaak["identificatie"],
                "url": ZAAK_URL,
            },
        )
