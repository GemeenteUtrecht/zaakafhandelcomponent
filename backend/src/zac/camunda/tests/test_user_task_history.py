from unittest.mock import patch

from django.urls import reverse

import requests_mock
from django_camunda.models import CamundaConfig
from django_camunda.utils import underscoreize
from furl import furl
from requests.exceptions import HTTPError
from rest_framework.test import APITestCase, APITransactionTestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen

from zac.accounts.tests.factories import (
    BlueprintPermissionFactory,
    SuperUserFactory,
    UserFactory,
)
from zac.camunda.data import Task
from zac.camunda.user_tasks.history import (
    get_completed_user_tasks_for_zaak,
    get_historic_activity_variables_from_task,
    get_task_history_for_process_instance,
)
from zac.core.permissions import zaken_inzien

from .files.harvo_behandelen import HARVO_BEHANDELEN_BPMN

DOCUMENTS_ROOT = "http://documents.nl/api/v1/"
ZAKEN_ROOT = "http://zaken.nl/api/v1/"
CATALOGI_ROOT = "https://open-zaak.nl/catalogi/api/v1/"
ZAAK_URL = "https://some.zrc.nl/api/v1/zaken/a955573e-ce3f-4cf3-8ae0-87853d61f47a"
CAMUNDA_ROOT = "https://camunda.example.com/"
CAMUNDA_API_PATH = "engine-rest/"
CAMUNDA_URL = f"{CAMUNDA_ROOT}{CAMUNDA_API_PATH}"


# Taken from https://docs.camunda.org/manual/7.13/reference/rest/history/task/get-task-query/
COMPLETED_TASK_DATA = {
    "id": "1790e564-8b57-11ec-baad-6ed7f836cf1f",
    "processDefinitionKey": "HARVO_behandelen",
    "processDefinitionId": "HARVO_behandelen:61:54586277-7922-11ec-8209-aa9470edda89",
    "processInstanceId": "0df2bc16-8b57-11ec-baad-6ed7f836cf1f",
    "executionId": "0df2bc16-8b57-11ec-baad-6ed7f836cf1f",
    "caseDefinitionKey": None,
    "caseDefinitionId": None,
    "caseInstanceId": None,
    "caseExecutionId": None,
    "activityInstanceId": "Activity_0bkealj:1790e563-8b57-11ec-baad-6ed7f836cf1f",
    "name": "Inhoudelijk voorbereiden (= checkvragen)",
    "description": None,
    "deleteReason": "completed",
    "owner": None,
    "assignee": "ammer001",
    "startTime": "2022-02-11T16:24:31.545+0000",
    "endTime": "2022-02-11T16:24:43.006+0000",
    "duration": 11461,
    "taskDefinitionKey": "Activity_0bkealj",
    "priority": 50,
    "due": None,
    "parentTaskId": None,
    "followUp": None,
    "tenantId": None,
    "removalTime": None,
    "rootProcessInstanceId": "0df2bc16-8b57-11ec-baad-6ed7f836cf1f",
}


@requests_mock.Mocker()
class UserTaskHistoryTests(APITransactionTestCase):
    def setUp(self) -> None:
        super().setUp()
        config = CamundaConfig.get_solo()
        config.root_url = CAMUNDA_ROOT
        config.rest_api_path = CAMUNDA_API_PATH
        config.save()

    def test_success_get_task_history_for_process_instance(self, m):
        m.get(
            f"{CAMUNDA_URL}history/task?processInstanceId={COMPLETED_TASK_DATA['processInstanceId']}&finished=true",
            json=[COMPLETED_TASK_DATA],
        )
        tasks = get_task_history_for_process_instance(
            COMPLETED_TASK_DATA["processInstanceId"]
        )
        self.assertEqual(
            tasks, {COMPLETED_TASK_DATA["id"]: underscoreize(COMPLETED_TASK_DATA)}
        )

    def test_fail_500_on_get_task_history_for_process_instance(self, m):
        m.get(
            f"{CAMUNDA_URL}history/task?processInstanceId={COMPLETED_TASK_DATA['processInstanceId']}&finished=true",
            json=[],
            status_code=500,
        )
        with self.assertRaises(HTTPError) as exc:
            get_task_history_for_process_instance(
                COMPLETED_TASK_DATA["processInstanceId"]
            )
        self.assertEqual(exc.exception.response.status_code, 500)

    def test_success_get_completed_user_tasks_for_zaak(self, m):
        # Mock historic process instances
        m.get(
            f"{CAMUNDA_URL}history/process-instance?variables=zaakUrl_eq_https%3A%2F%2Fsome.zrc.nl%2Fapi%2Fv1%2Fzaken%2Fa955573e-ce3f-4cf3-8ae0-87853d61f47a",
            json=[{"id": COMPLETED_TASK_DATA["processInstanceId"]}],
        )
        m.get(
            f"{CAMUNDA_URL}history/process-instance?superProcessInstanceId={COMPLETED_TASK_DATA['processInstanceId']}",
            json=[],
        )
        # Mock current process instances
        m.get(
            f"{CAMUNDA_URL}process-instance?variables=zaakUrl_eq_https%3A%2F%2Fsome.zrc.nl%2Fapi%2Fv1%2Fzaken%2Fa955573e-ce3f-4cf3-8ae0-87853d61f47a",
            json=[],
        )
        # Mock completed tasks from historic process instances
        m.get(
            f"{CAMUNDA_URL}history/task?processInstanceId={COMPLETED_TASK_DATA['processInstanceId']}&finished=true",
            json=[COMPLETED_TASK_DATA],
        )
        tasks = get_completed_user_tasks_for_zaak(ZAAK_URL)
        self.assertEqual(
            str(list(tasks.keys())[0]), "1790e564-8b57-11ec-baad-6ed7f836cf1f"
        )
        self.assertTrue(
            isinstance(list(tasks.values())[0], Task),
        )

    def test_success_get_historic_activity_variables_from_task(self, m):
        # Mock historic activity details
        m.get(
            f"{CAMUNDA_URL}history/detail?activityInstanceId={COMPLETED_TASK_DATA['activityInstanceId']}&deserializeValues=False",
            json=[
                {
                    "type": "variableUpdate",
                    "id": "1e653f89-8b57-11ec-baad-6ed7f836cf1f",
                    "processDefinitionKey": "HARVO_behandelen",
                    "processDefinitionId": "HARVO_behandelen:61:54586277-7922-11ec-8209-aa9470edda89",
                    "processInstanceId": "0df2bc16-8b57-11ec-baad-6ed7f836cf1f",
                    "activityInstanceId": "Activity_0bkealj:1790e563-8b57-11ec-baad-6ed7f836cf1f",
                    "executionId": "0df2bc16-8b57-11ec-baad-6ed7f836cf1f",
                    "caseDefinitionKey": None,
                    "caseDefinitionId": None,
                    "caseInstanceId": None,
                    "caseExecutionId": None,
                    "taskId": None,
                    "tenantId": None,
                    "userOperationId": "1e653f88-8b57-11ec-baad-6ed7f836cf1f",
                    "time": "2022-02-11T16:24:43.001+0000",
                    "removalTime": None,
                    "rootProcessInstanceId": "0df2bc16-8b57-11ec-baad-6ed7f836cf1f",
                    "variableName": "checkIntegriteit",
                    "variableInstanceId": "1e653f87-8b57-11ec-baad-6ed7f836cf1f",
                    "variableType": "String",
                    "value": "Ja",
                    "valueInfo": {},
                    "revision": 0,
                    "errorMessage": None,
                }
            ],
        )
        historic_activity_details = get_historic_activity_variables_from_task(
            factory(
                Task,
                underscoreize(
                    {
                        **COMPLETED_TASK_DATA,
                        "created": COMPLETED_TASK_DATA["startTime"],
                        "delegationState": None,
                        "suspended": True,
                        "formKey": None,
                    }
                ),
            )
        )
        self.assertEqual(len(historic_activity_details), 1)
        self.assertEqual(
            historic_activity_details[0]["variable_name"],
            "checkIntegriteit",
        )
        self.assertEqual(historic_activity_details[0]["value"], "Ja")

    def test_fail_get_user_task_history_missing_query_parameter(self, m):
        user = SuperUserFactory.create()
        self.client.force_authenticate(user)
        url = furl(reverse("user-task-history"))
        response = self.client.get(url.url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), ["Missing the zaak URL query parameter."])

    def test_success_get_user_task_history(self, m):
        # Mocks for get_completed_user_tasks_for_zaak
        m.get(
            f"{CAMUNDA_URL}history/process-instance?variables=zaakUrl_eq_{ZAAK_URL}",
            json=[{"id": COMPLETED_TASK_DATA["processInstanceId"]}],
        )
        m.get(
            f"{CAMUNDA_URL}history/process-instance?superProcessInstanceId={COMPLETED_TASK_DATA['processInstanceId']}",
            json=[],
        )
        # Mock current process instances
        m.get(
            f"{CAMUNDA_URL}process-instance?variables=zaakUrl_eq_{ZAAK_URL}",
            json=[],
        )
        # Mock completed tasks from historic process instances
        m.get(
            f"{CAMUNDA_URL}history/task?processInstanceId={COMPLETED_TASK_DATA['processInstanceId']}&finished=true",
            json=[COMPLETED_TASK_DATA],
        )

        # Mock for extract_task_form_key
        m.get(
            f"{CAMUNDA_URL}process-definition/HARVO_behandelen:61:54586277-7922-11ec-8209-aa9470edda89/xml",
            json={"bpmn20_xml": HARVO_BEHANDELEN_BPMN},
        )

        # Mock historic activity details
        m.get(
            f"{CAMUNDA_URL}history/detail?activityInstanceId={COMPLETED_TASK_DATA['activityInstanceId']}&deserializeValues=False",
            json=[
                {
                    "type": "variableUpdate",
                    "id": "1e653f89-8b57-11ec-baad-6ed7f836cf1f",
                    "processDefinitionKey": "HARVO_behandelen",
                    "processDefinitionId": "HARVO_behandelen:61:54586277-7922-11ec-8209-aa9470edda89",
                    "processInstanceId": "0df2bc16-8b57-11ec-baad-6ed7f836cf1f",
                    "activityInstanceId": "Activity_0bkealj:1790e563-8b57-11ec-baad-6ed7f836cf1f",
                    "executionId": "0df2bc16-8b57-11ec-baad-6ed7f836cf1f",
                    "caseDefinitionKey": None,
                    "caseDefinitionId": None,
                    "caseInstanceId": None,
                    "caseExecutionId": None,
                    "taskId": None,
                    "tenantId": None,
                    "userOperationId": "1e653f88-8b57-11ec-baad-6ed7f836cf1f",
                    "time": "2022-02-11T16:24:43.001+0000",
                    "removalTime": None,
                    "rootProcessInstanceId": "0df2bc16-8b57-11ec-baad-6ed7f836cf1f",
                    "variableName": "checkIntegriteit",
                    "variableInstanceId": "1e653f87-8b57-11ec-baad-6ed7f836cf1f",
                    "variableType": "String",
                    "value": "Ja",
                    "valueInfo": {},
                    "revision": 0,
                    "errorMessage": None,
                }
            ],
        )

        url = furl(reverse("user-task-history"))
        url.set({"zaak_url": ZAAK_URL})
        user = SuperUserFactory.create()
        self.client.force_authenticate(user)
        response = self.client.get(url.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            [
                {
                    "assignee": {
                        "id": 2,
                        "username": "ammer001",
                        "firstName": "",
                        "fullName": "",
                        "lastName": "",
                        "isStaff": False,
                        "email": "",
                        "groups": [],
                    },
                    "completed": "2022-02-11T16:24:43.006000Z",
                    "created": "2022-02-11T16:24:31.545000Z",
                    "name": "Inhoudelijk voorbereiden (= checkvragen)",
                    "history": [
                        {
                            "naam": "checkIntegriteit",
                            "waarde": "Ja",
                            "label": "Is de integriteit van de wederpartij getoetst?",
                        }
                    ],
                }
            ],
        )


@requests_mock.Mocker()
class UserTaskHistoryPermissionTests(APITestCase):
    def test_no_user_logged_in(self, m):
        url = furl(reverse("user-task-history"))
        url.set({"zaak_url": ZAAK_URL})
        response = self.client.get(url.url)
        self.assertEqual(response.status_code, 403)

    def test_user_logged_in_but_no_permission(self, m):
        url = furl(reverse("user-task-history"))
        url.set({"zaak_url": ZAAK_URL})
        user = UserFactory.create()
        self.client.force_authenticate(user)
        response = self.client.get(url.url)
        self.assertEqual(response.status_code, 403)

    def test_user_logged_in_with_permission(self, m):
        user = UserFactory.create()
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=user,
            policy={
                "catalogus": "https://some-catalogus.nl/",
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        self.client.force_authenticate(user)

        url = furl(reverse("user-task-history"))
        url.set({"zaak_url": ZAAK_URL})
        with patch(
            "zac.camunda.api.views.get_camunda_history_for_zaak", return_value=[]
        ):
            response = self.client.get(url.url)
        self.assertEqual(response.status_code, 200)
