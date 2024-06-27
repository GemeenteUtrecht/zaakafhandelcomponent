from unittest.mock import patch

from django.urls import reverse

import requests_mock
from django_camunda.client import get_client
from django_camunda.models import CamundaConfig
from rest_framework.test import APITestCase

from zac.accounts.tests.factories import UserFactory
from zac.core.tests.utils import ClearCachesMixin

BPMN_DATA = {
    "id": "Adhoc_vergaderen:1:2ee97bc4-a370-11eb-970c-6a0042b17f4a",
    "bpmn20_xml": '<?xml version="1.0" encoding="UTF-8"?>\n<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" xmlns:camunda="http://camunda.org/schema/1.0/bpmn" xmlns:di="http://www.omg.org/spec/DD/20100524/DI" xmlns:bioc="http://bpmn.io/schema/bpmn/biocolor/1.0" id="Definitions_0ukdc2m" targetNamespace="http://bpmn.io/schema/bpmn" exporter="Camunda Modeler" exporterVersion="4.6.0">\n  <bpmn:collaboration id="Collaboration_02wzhhk">\n    <bpmn:participant id="adhoc-vergaderen" name="Ad Hoc vergaderen" processRef="Adhoc_vergaderen" />\n  </bpmn:collaboration>\n <bpmndi:BPMNDiagram id="BPMNDiagram_1">\n <bpmndi:BPMNPlane id="BPMNPlane_1" bpmnElement="Collaboration_02wzhhk">\n </bpmndi:BPMNPlane>\n  </bpmndi:BPMNDiagram>\n</bpmn:definitions>',
}
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
class GetBPMNViewTests(ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory.create()
        cls.patch_get_client_bpmn = patch(
            "django_camunda.bpmn.get_client", return_value=_get_camunda_client()
        )

    def setUp(self) -> None:
        super().setUp()
        self.client.force_authenticate(self.user)
        self.patch_get_client_bpmn.start()
        self.addCleanup(self.patch_get_client_bpmn.stop)

    def test_get_bpmn_success(self, m):
        user = UserFactory.create()
        m.get(
            f"{CAMUNDA_URL}process-definition/Adhoc_vergaderen:1:2ee97bc4-a370-11eb-970c-6a0042b17f4a/xml",
            json=BPMN_DATA,
        )
        self.client.force_authenticate(user=user)
        endpoint = reverse(
            "bpmn",
            kwargs={
                "process_definition_id": "Adhoc_vergaderen:1:2ee97bc4-a370-11eb-970c-6a0042b17f4a"
            },
        )
        response = self.client.get(endpoint)
        self.assertEqual(
            response.json(),
            {"id": BPMN_DATA["id"], "bpmn20Xml": BPMN_DATA["bpmn20_xml"]},
        )

    def test_get_bpmn_does_not_exist(self, m):
        user = UserFactory.create()
        m.get(
            f"{CAMUNDA_URL}process-definition/Adhoc_vergaderen:1:2ee97bc4-a370-11eb-970c-6a0042b17f4a/xml",
            json={
                "type": "InvalidRequestException",
                "message": "No matching definition with id Adhoc_vergaderen:1:2ee97bc4-a370-11eb-970c-6a0042b17f4b",
            },
            status_code=400,
        )
        self.client.force_authenticate(user=user)
        endpoint = reverse(
            "bpmn",
            kwargs={
                "process_definition_id": "Adhoc_vergaderen:1:2ee97bc4-a370-11eb-970c-6a0042b17f4a"
            },
        )
        response = self.client.get(endpoint)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "type",
                    "code": "invalid",
                    "reason": "InvalidRequestException",
                },
                {
                    "name": "message",
                    "code": "invalid",
                    "reason": "No matching definition with id Adhoc_vergaderen:1:2ee97bc4-a370-11eb-970c-6a0042b17f4b",
                },
            ],
        )
