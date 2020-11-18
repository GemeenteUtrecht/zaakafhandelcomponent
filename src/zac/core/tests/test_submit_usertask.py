import base64
import json
import uuid
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

import requests_mock
from django_camunda.utils import serialize_variable
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType

from zac.accounts.tests.factories import SuperUserFactory
from zac.core.tests.utils import ClearCachesMixin
from zac.tests.utils import generate_oas_component
from zgw.models import Zaak

TASK = {
    "name": "aName",
    "created": "2013-01-23T13:42:42.000+0200",
    "due": "2013-01-23T13:49:42.576+0200",
    "followUp": "2013-01-23T13:44:42.437+0200",
    "delegationState": "RESOLVED",
    "description": "",
    "executionId": "",
    "owner": "anOwner",
    "parentTaskId": None,
    "priority": 50,
    "processDefinitionId": "aProcDefId",
    "caseDefinitionId": "aCaseDefId",
    "caseInstanceId": "aCaseInstId",
    "caseExecutionId": "aCaseExecution",
    "taskDefinitionKey": "aTaskDefinitionKey",
    "suspended": False,
    "formKey": "zac:doRedirect",
    "tenantId": "aTenantId",
}

HISTORIC_TASK = {
    "processDefinitionId": "aProcDefId",
    "executionId": "anExecution",
    "caseDefinitionId": "aCaseDefId",
    "caseInstanceId": "aCaseInstId",
    "caseExecutionId": "aCaseExecution",
    "activityInstanceId": "anActInstId",
    "name": "aName",
    "description": "aDescription",
    "deleteReason": "aDeleteReason",
    "owner": "anOwner",
    "startTime": "2013-01-23T13:42:42.000+0200",
    "endTime": "2013-01-23T13:45:42.000+0200",
    "duration": 2000,
    "taskDefinitionKey": "aTaskDefinitionKey",
    "priority": 42,
    "due": "2013-01-23T13:49:42.000+0200",
    "parentTaskId": None,
    "followUp": "2013-01-23T13:44:42.000+0200",
    "tenantId": None,
    "removalTime": "2018-02-10T14:33:19.000+0200",
    "rootProcessInstanceId": "aRootProcessInstanceId",
}


@requests_mock.Mocker()
class SubmitRedirectUserTaskTests(ClearCachesMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = SuperUserFactory.create()

    def setUp(self):
        super().setUp()
        self.client.force_login(user=self.user)

        extract_form_patcher = patch(
            "zac.core.camunda.extract_task_form", return_value=None
        )
        extract_form_patcher.start()
        self.addCleanup(extract_form_patcher.stop)

    def test_task_not_yet_completed(self, m):
        """
        Test that the redirect task view completes the task when needed.
        """
        # set up the Camunda mocks for a "live" task
        PROCESS_INSTANCE_ID = "f0a2e2c4-b35c-49f1-9fba-aaa7a161f247"
        ZAAK_URL = "https://open-zaak.nl/zaken/api/v1/zaken/1234"
        task_id = str(uuid.uuid4())
        url = reverse("core:redirect-task", kwargs={"task_id": task_id})
        state = json.dumps(
            {
                "user_id": self.user.id,
                "task_id": task_id,
            }
        ).encode("utf-8")
        m.get(
            f"https://camunda.example.com/engine-rest/task/{task_id}",
            json={
                **TASK,
                "id": task_id,
                "assignee": self.user.username,
                "processInstanceId": PROCESS_INSTANCE_ID,
            },
        )
        m.get(
            f"https://camunda.example.com/engine-rest/process-instance/{PROCESS_INSTANCE_ID}",
            json={
                "id": PROCESS_INSTANCE_ID,
                "definitionId": "proces:1",
                "businessKey": "",
                "caseInstanceId": "",
                "suspended": False,
                "tenantId": "",
            },
        )
        m.get(
            (
                "https://camunda.example.com/engine-rest/process-instance/"
                f"{PROCESS_INSTANCE_ID}/variables/zaakUrl?deserializeValues=false"
            ),
            json=serialize_variable(ZAAK_URL),
        )

        zaaktype = factory(ZaakType, generate_oas_component("ztc", "schemas/ZaakType"))
        zaak = factory(
            Zaak,
            generate_oas_component(
                "zrc",
                "schemas/Zaak",
                url=ZAAK_URL,
                zaaktype=zaaktype.url,
            ),
        )

        with patch("zac.core.views.processes.get_zaak", return_value=zaak), patch(
            "zac.core.views.processes.fetch_zaaktype", return_value=zaaktype
        ), patch("zac.core.views.processes.complete_task") as mock_complete_task:
            response = self.client.get(url, {"state": base64.b64encode(state)})

            expected_url = reverse(
                "core:zaak-detail",
                kwargs={
                    "bronorganisatie": zaak.bronorganisatie,
                    "identificatie": zaak.identificatie,
                },
            )
            self.assertRedirects(response, expected_url, fetch_redirect_response=False)

        mock_complete_task.assert_called_once_with(uuid.UUID(task_id), {})

    def test_task_already_completed(self, m):
        # set up the Camunda mocks for a "completed" task (because of webhook, for example)
        PROCESS_INSTANCE_ID = "f0a2e2c4-b35c-49f1-9fba-aaa7a161f247"
        ZAAK_URL = "https://open-zaak.nl/zaken/api/v1/zaken/1234"
        task_id = str(uuid.uuid4())
        url = reverse("core:redirect-task", kwargs={"task_id": task_id})
        state = json.dumps(
            {
                "user_id": self.user.id,
                "task_id": task_id,
            }
        ).encode("utf-8")
        m.get(
            f"https://camunda.example.com/engine-rest/task/{task_id}", status_code=404
        )
        m.get(
            f"https://camunda.example.com/engine-rest/process-instance/{PROCESS_INSTANCE_ID}",
            status_code=404,
        )
        m.get(
            f"https://camunda.example.com/engine-rest/history/task?taskId={task_id}",
            json=[
                {
                    **HISTORIC_TASK,
                    "id": task_id,
                    "assignee": self.user.username,
                    "processInstanceId": PROCESS_INSTANCE_ID,
                }
            ],
        )
        m.get(
            f"https://camunda.example.com/engine-rest/history/process-instance/{PROCESS_INSTANCE_ID}",
            json={
                "id": PROCESS_INSTANCE_ID,
                "processDefinitionId": "proces:1",
                "businessKey": "",
                "caseInstanceId": "",
                "state": "COMPLETED",
                "tenantId": "",
            },
        )
        m.get(
            (
                "https://camunda.example.com/engine-rest/history/variable-instance"
                f"?variableName=zaakUrl&deserializeValues=false&processInstanceId={PROCESS_INSTANCE_ID}"
            ),
            json=[
                {
                    "id": str(uuid.uuid4()),
                    "name": "zaakUrl",
                    "processInstanceId": PROCESS_INSTANCE_ID,
                    "createTime": timezone.now().isoformat(),
                    **serialize_variable(ZAAK_URL),
                }
            ],
        )
        zaaktype = factory(ZaakType, generate_oas_component("ztc", "schemas/ZaakType"))
        zaak = factory(
            Zaak,
            generate_oas_component(
                "zrc",
                "schemas/Zaak",
                url=ZAAK_URL,
                zaaktype=zaaktype.url,
            ),
        )

        with patch("zac.core.views.processes.get_zaak", return_value=zaak), patch(
            "zac.core.views.processes.fetch_zaaktype", return_value=zaaktype
        ), patch("zac.core.views.processes.complete_task") as mock_complete_task:
            response = self.client.get(url, {"state": base64.b64encode(state)})

            expected_url = reverse(
                "core:zaak-detail",
                kwargs={
                    "bronorganisatie": zaak.bronorganisatie,
                    "identificatie": zaak.identificatie,
                },
            )
            self.assertRedirects(response, expected_url, fetch_redirect_response=False)

        mock_complete_task.assert_not_called()
