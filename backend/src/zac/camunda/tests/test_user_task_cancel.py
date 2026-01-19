from unittest.mock import patch

from django.urls import reverse_lazy

import requests_mock
from django_camunda.models import CamundaConfig
from django_camunda.utils import serialize_variable
from rest_framework.test import APITestCase
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes

from zac.accounts.tests.factories import (
    BlueprintPermissionFactory,
    SuperUserFactory,
    UserFactory,
)
from zac.core.permissions import zaakproces_usertasks
from zac.core.tests.utils import ClearCachesMixin
from zac.tests import ServiceFactory
from zac.tests.compat import generate_oas_component, mock_service_oas_get
from zac.tests.utils import mock_resource_get

from .factories import KillableTaskFactory

CAMUNDA_ROOT = "https://some.camunda.nl/"
CAMUNDA_API_PATH = "engine-rest/"
CAMUNDA_URL = f"{CAMUNDA_ROOT}{CAMUNDA_API_PATH}"
ZAKEN_ROOT = "http://zaken.nl/api/v1/"
CATALOGI_ROOT = "http://catalogus.nl/api/v1/"


# Taken from https://docs.camunda.org/manual/7.13/reference/rest/history/task/get-task-query/
TASK_DATA = {
    "id": "fc9c465d-b0d7-11ec-a5f0-32fe9303dc32",
    "name": "Adviesvraag configureren",
    "assignee": None,
    "created": "2022-03-31T09:50:24.420+0000",
    "due": None,
    "follow_up": None,
    "delegation_state": None,
    "description": None,
    "execution_id": "fc9c4659-b0d7-11ec-a5f0-32fe9303dc32",
    "owner": None,
    "parent_task_id": None,
    "priority": 50,
    "process_definition_id": "Beleid_opstellen:6:85ff7b20-a149-11ec-a0c6-dec9c846e7c7",
    "process_instance_id": "134fa43d-b03e-11ec-a5f0-32fe9303dc32",
    "task_definition_key": "Activity_1ltd2rq",
    "case_execution_id": None,
    "case_instance_id": None,
    "case_definition_id": None,
    "suspended": False,
    "form_key": "zac:configureAdviceRequest",
    "tenant_id": None,
}

HISTORY_TASK_DATA = [
    {
        "id": "fc9c465d-b0d7-11ec-a5f0-32fe9303dc32",
        "processDefinitionKey": "Beleid_opstellen",
        "processDefinitionId": "Beleid_opstellen:6:85ff7b20-a149-11ec-a0c6-dec9c846e7c7",
        "processInstanceId": "134fa43d-b03e-11ec-a5f0-32fe9303dc32",
        "executionId": "fc9c4659-b0d7-11ec-a5f0-32fe9303dc32",
        "caseDefinitionKey": None,
        "caseDefinitionId": None,
        "caseInstanceId": None,
        "caseExecutionId": None,
        "activityInstanceId": "Activity_1ltd2rq:fc9c465c-b0d7-11ec-a5f0-32fe9303dc32",
        "name": "Adviesvraag configureren",
        "description": None,
        "deleteReason": None,
        "owner": None,
        "assignee": None,
        "startTime": "2022-03-31T09:50:24.420+0000",
        "endTime": None,
        "duration": None,
        "taskDefinitionKey": "Activity_1ltd2rq",
        "priority": 50,
        "due": None,
        "parentTaskId": None,
        "followUp": None,
        "tenantId": None,
        "removalTime": None,
        "rootProcessInstanceId": "134fa43d-b03e-11ec-a5f0-32fe9303dc32",
    }
]


@requests_mock.Mocker()
class CancelTaskViewTests(ClearCachesMixin, APITestCase):
    url = reverse_lazy("cancel-task")

    def setUp(self) -> None:
        super().setUp()
        config = CamundaConfig.get_solo()
        config.root_url = CAMUNDA_ROOT
        config.rest_api_path = CAMUNDA_API_PATH
        config.save()
        self.user = SuperUserFactory.create(username="some-user")
        self.client.force_authenticate(self.user)

    def test_fail_get_task(self, m):
        m.get(
            f"{CAMUNDA_URL}task/fc9c465d-b0d7-11ec-a5f0-32fe9303dc32",
            json={
                "type": "InvalidRequestException",
                "message": "No matching task with id fc9c465d-b0d7-11ec-a5f0-32fe9303dc32",
            },
            status_code=404,
        )
        response = self.client.post(
            self.url, data={"task": "fc9c465d-b0d7-11ec-a5f0-32fe9303dc32"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "code": "invalid",
                    "name": "task",
                    "reason": "No task found for id "
                    "`fc9c465d-b0d7-11ec-a5f0-32fe9303dc32`",
                }
            ],
        )

    def test_user_task_is_not_killable(self, m):
        m.get(
            f"{CAMUNDA_URL}task/fc9c465d-b0d7-11ec-a5f0-32fe9303dc32",
            json=TASK_DATA,
        )
        m.get(
            f"{CAMUNDA_URL}history/task?taskId=fc9c465d-b0d7-11ec-a5f0-32fe9303dc32",
            json=HISTORY_TASK_DATA,
        )
        m.post(
            f"{CAMUNDA_URL}process-instance/134fa43d-b03e-11ec-a5f0-32fe9303dc32/modification",
            status_code=204,
        )
        ServiceFactory.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
        )
        m.get(
            f"{CAMUNDA_URL}task/fc9c465d-b0d7-11ec-a5f0-32fe9303dc32/variables/zaakUrl?deserializeValue=false",
            json=serialize_variable(zaak["url"]),
        )
        m.get(zaak["url"], json=zaak)

        response = self.client.post(
            self.url, data={"task": "fc9c465d-b0d7-11ec-a5f0-32fe9303dc32"}
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "code": "invalid",
                    "name": "task",
                    "reason": "Taak `Adviesvraag configureren` kan niet worden "
                    "geannuleerd.",
                }
            ],
        )

    def test_cancel_user_task(self, m):
        killable_task = KillableTaskFactory.create()
        m.get(
            f"{CAMUNDA_URL}task/fc9c465d-b0d7-11ec-a5f0-32fe9303dc32",
            json={**TASK_DATA, "name": killable_task.name},
        )
        m.post(
            f"{CAMUNDA_URL}history/task",
            json=[{**HISTORY_TASK_DATA[0], "name": killable_task.name}],
        )
        m.post(
            f"{CAMUNDA_URL}process-instance/134fa43d-b03e-11ec-a5f0-32fe9303dc32/modification",
            status_code=204,
        )
        ServiceFactory.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
        )
        m.get(
            f"{CAMUNDA_URL}task/fc9c465d-b0d7-11ec-a5f0-32fe9303dc32/variables/zaakUrl?deserializeValue=false",
            json=serialize_variable(zaak["url"]),
        )
        m.get(zaak["url"], json=zaak)

        response = self.client.post(
            self.url, data={"task": "fc9c465d-b0d7-11ec-a5f0-32fe9303dc32"}
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(
            m.last_request.json(),
            {
                "skipIoMappings": "true",
                "instructions": [
                    {
                        "type": "cancel",
                        "activityInstanceId": "Activity_1ltd2rq:fc9c465c-b0d7-11ec-a5f0-32fe9303dc32",
                    }
                ],
            },
        )


class CancelTaskPermissionsTests(ClearCachesMixin, APITestCase):
    url = reverse_lazy("cancel-task")

    def setUp(self) -> None:
        super().setUp()
        config = CamundaConfig.get_solo()
        config.root_url = CAMUNDA_ROOT
        config.rest_api_path = CAMUNDA_API_PATH
        config.save()

    def test_no_user_logged_in(self):
        response = self.client.post(self.url, data={})
        self.assertEqual(response.status_code, 403)

    def test_user_logged_in_but_no_permission_to_perform_task(self):
        user = UserFactory.create()
        self.client.force_authenticate(user)
        response = self.client.post(self.url, data={})
        self.assertEqual(response.status_code, 403)

    @requests_mock.Mocker()
    def test_user_logged_in_with_permission(self, m):
        ServiceFactory.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        ServiceFactory.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)

        catalogus = generate_oas_component(
            "ztc",
            "schemas/Catalogus",
            url=f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd",
            domein="DOME",
        )
        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=catalogus["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT1",
        )
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            zaaktype=zaaktype["url"],
        )
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, catalogus)
        mock_resource_get(m, zaaktype)
        mock_resource_get(m, zaak)

        killable_task = KillableTaskFactory.create()
        m.get(
            f"{CAMUNDA_URL}task/fc9c465d-b0d7-11ec-a5f0-32fe9303dc32",
            json={**TASK_DATA, "name": killable_task.name},
        )
        m.get(
            f"{CAMUNDA_URL}history/task?taskId=fc9c465d-b0d7-11ec-a5f0-32fe9303dc32",
            json=[{**HISTORY_TASK_DATA[0], "name": killable_task.name}],
        )
        user = UserFactory.create()
        BlueprintPermissionFactory.create(
            role__permissions=[zaakproces_usertasks.name],
            for_user=user,
            policy={
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        m.get(
            f"{CAMUNDA_URL}task/fc9c465d-b0d7-11ec-a5f0-32fe9303dc32/variables/zaakUrl?deserializeValue=false",
            json=serialize_variable(zaak["url"]),
        )

        self.client.force_authenticate(user)
        with patch(
            "zac.camunda.api.views.cancel_activity_instance_of_task", return_value=None
        ):
            response = self.client.post(
                self.url, data={"task": "fc9c465d-b0d7-11ec-a5f0-32fe9303dc32"}
            )
        self.assertEqual(response.status_code, 204)
