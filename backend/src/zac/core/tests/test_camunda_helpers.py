from django.test import TestCase

import requests_mock
from django_camunda.utils import serialize_variable

from zac.camunda.data import ProcessInstance

from ..camunda.utils import get_process_zaak_url

PI_URL = "https://camunda.example.com/engine-rest/process-instance"


@requests_mock.Mocker()
class GetProcessZaakUrlTests(TestCase):
    def test_variable_on_subprocess(self, m):
        process = ProcessInstance(
            id="aProcessInstanceId", definition_id="some-process:1"
        )
        m.get(
            f"{PI_URL}/aProcessInstanceId/variables/zaakUrl?deserializeValue=false",
            json=serialize_variable("dummy"),
        )

        zaak_url = get_process_zaak_url(process)

        self.assertEqual(zaak_url, "dummy")

    def test_variable_on_parent_process(self, m):
        process = ProcessInstance(
            id="aProcessInstanceId", definition_id="some-process:1"
        )
        m.get(
            f"{PI_URL}/aProcessInstanceId/variables/zaakUrl?deserializeValue=false",
            status_code=404,
        )
        m.get(
            f"{PI_URL}?subProcessInstance=aProcessInstanceId",
            json=[
                {
                    "id": "parentProcessInstanceId",
                    "definitionId": "parent-process:1",
                }
            ],
        )
        m.get(
            f"{PI_URL}/parentProcessInstanceId/variables/zaakUrl?deserializeValue=false",
            json=serialize_variable("dummy"),
        )

        zaak_url = get_process_zaak_url(process)

        self.assertEqual(zaak_url, "dummy")

    def test_variable_nowhere(self, m):
        process = ProcessInstance(
            id="aProcessInstanceId", definition_id="some-process:1"
        )
        m.get(
            f"{PI_URL}/aProcessInstanceId/variables/zaakUrl?deserializeValue=false",
            status_code=404,
        )
        m.get(f"{PI_URL}?subProcessInstance=aProcessInstanceId", json=[])

        with self.assertRaises(RuntimeError):
            get_process_zaak_url(process)
