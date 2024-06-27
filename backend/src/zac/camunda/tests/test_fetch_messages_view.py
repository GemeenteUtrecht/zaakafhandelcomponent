from unittest.mock import patch

from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

import requests_mock
from django_camunda.client import get_client
from django_camunda.models import CamundaConfig
from rest_framework import status
from rest_framework.test import APITestCase

from zac.accounts.tests.factories import UserFactory
from zac.core.tests.utils import ClearCachesMixin

from .files.harvo_behandelen import HARVO_BEHANDELEN_BPMN
from .files.no_form import NO_FORM_BPMN

ZAKEN_ROOT = "https://some.zrc.nl/api/v1/"
ZAAK_URL = f"{ZAKEN_ROOT}zaken/a955573e-ce3f-4cf3-8ae0-87853d61f47a"
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
class FetchMessagesTests(ClearCachesMixin, APITestCase):
    url = reverse_lazy("fetch-messages")

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory.create()
        cls.patch_get_camunda_client = [
            patch(
                "zac.camunda.messages.get_client", return_value=_get_camunda_client()
            ),
            patch("django_camunda.bpmn.get_client", return_value=_get_camunda_client()),
        ]

    def setUp(self) -> None:
        super().setUp()
        self.client.force_authenticate(self.user)
        for patcher in self.patch_get_camunda_client:
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_not_logged_in(self, m_request):
        self.client.logout()
        response = self.client.get(self.url, {"zaakUrl": ZAAK_URL})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_fail_fetch_process_instances_no_zaak_url(self, m_request):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["invalidParams"],
            [{"code": "required", "name": "zaakUrl", "reason": "Dit veld is vereist."}],
        )

    def test_fetch_messages(self, m_request):
        process_definition = {
            "id": f"HARVO_behandelen:8:c76c8200-c766-11ea-86dc-e22fafe5f405",
            "key": "HARVO_behandelen",
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
        process_instance_data = [
            {
                "id": "205eae6b-d26f-11ea-86dc-e22fafe5f405",
                "definitionId": process_definition["id"],
                "businessKey": "",
                "caseInstanceId": "",
                "suspended": False,
                "tenantId": "",
            },
        ]
        m_request.post(f"{CAMUNDA_URL}process-instance", json=process_instance_data)
        m_request.get(
            f"{CAMUNDA_URL}process-definition/{process_definition['id']}/xml",
            json={"bpmn20_xml": HARVO_BEHANDELEN_BPMN},
        )
        response = self.client.get(self.url, {"zaakUrl": ZAAK_URL})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(
            response.json(),
            [
                {
                    "id": process_instance_data[0]["id"],
                    "messages": ["Annuleer behandeling", "Advies vragen"],
                }
            ],
        )

    def test_fetch_process_instances_no_process_instance(self, m_request):
        process_instance_data = []
        m_request.post(f"{CAMUNDA_URL}process-instance", json=process_instance_data)
        response = self.client.get(self.url, {"zaakUrl": ZAAK_URL})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), [])

    def test_fetch_process_instances_no_messages(self, m_request):
        process_definition = {
            "id": f"HARVO_behandelen:8:c76c8200-c766-11ea-86dc-e22fafe5f405",
            "key": "HARVO_behandelen",
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
        process_instance_data = [
            {
                "id": "205eae6b-d26f-11ea-86dc-e22fafe5f405",
                "definitionId": process_definition["id"],
                "businessKey": "",
                "caseInstanceId": "",
                "suspended": False,
                "tenantId": "",
            },
        ]
        m_request.post(f"{CAMUNDA_URL}process-instance", json=process_instance_data)
        m_request.get(
            f"{CAMUNDA_URL}process-definition/{process_definition['id']}/xml",
            json={"bpmn20_xml": NO_FORM_BPMN},
        )
        response = self.client.get(self.url, {"zaakUrl": ZAAK_URL})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            [{"id": "205eae6b-d26f-11ea-86dc-e22fafe5f405", "messages": []}],
        )
