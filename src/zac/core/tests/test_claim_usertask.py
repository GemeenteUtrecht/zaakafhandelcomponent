import uuid
from datetime import date
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse_lazy

import requests_mock

from zac.accounts.tests.factories import SuperUserFactory, UserFactory
from zgw.models import Zaak

from .mocks import get_camunda_task_mock


@requests_mock.Mocker()
class BPMNMessageSendTests(TestCase):
    url = reverse_lazy("core:claim-task")

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = SuperUserFactory.create()

    def setUp(self):
        super().setUp()
        self.client.force_login(user=self.user)

    @patch("zac.core.camunda.extract_task_form", return_value=None)
    @patch("zac.core.views.processes.get_roltypen", return_value=[])
    @patch("zac.core.views.processes.fetch_zaaktype", return_value=None)
    @patch("zac.core.views.processes.get_zaak")
    def test_claim_task_ok(self, m, m_get_zaak, *other_mocks):
        TASK_ID = str(uuid.uuid4())
        PROCESS_INSTANCE_ID = str(uuid.uuid4())
        ZAAK_URL = "https://open-zaak.nl/zaken/api/v1/zaken/1234"
        # MOCKS
        m.get(
            f"https://camunda.example.com/engine-rest/task/{TASK_ID}",
            json=get_camunda_task_mock(
                id=TASK_ID, process_instance_id=PROCESS_INSTANCE_ID
            ),
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
            json={"value": ZAAK_URL, "type": "String"},
        )
        m_get_zaak.return_value = Zaak(
            url=ZAAK_URL,
            identificatie="0001",
            bronorganisatie="123456782",
            omschrijving="",
            toelichting="",
            zaaktype="https://open-zaak.nl/catalogi/api/v1/zaaktypen/123",
            registratiedatum=date.today(),
            startdatum=date.today(),
            einddatum=None,
            einddatum_gepland=None,
            uiterlijke_einddatum_afdoening=None,
            publicatiedatum=None,
            vertrouwelijkheidaanduiding="openbaar",
            status="",
            resultaat="",
            relevante_andere_zaken=[],
            zaakgeometrie={},
        )
        m.post(
            f"https://camunda.example.com/engine-rest/task/{TASK_ID}/claim",
            status_code=204,
        )

        # ACTUAL HTTP calls
        response = self.client.post(
            self.url,
            {"task_id": TASK_ID},
            HTTP_REFERER="http://testserver/",
        )

        # ASSERTIONS
        self.assertEqual(response.status_code, 302)

    def test_task_does_not_exist(self, m):
        TASK_ID = str(uuid.uuid4())
        m.get(
            f"https://camunda.example.com/engine-rest/task/{TASK_ID}",
            status_code=404,
        )

        response = self.client.post(
            self.url,
            {"task_id": TASK_ID},
            HTTP_REFERER="http://testserver/",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["task_id"][0]["message"], "Invalid task referenced."
        )

    @patch("zac.core.camunda.extract_task_form", return_value=None)
    @patch("zac.core.views.processes.get_zaak")
    def test_no_permission(self, m, m_get_zaak, *other_mocks):
        TASK_ID = str(uuid.uuid4())
        PROCESS_INSTANCE_ID = str(uuid.uuid4())
        ZAAK_URL = "https://open-zaak.nl/zaken/api/v1/zaken/1234"
        user = UserFactory.create()
        self.client.force_login(user)
        # MOCKS
        m.get(
            f"https://camunda.example.com/engine-rest/task/{TASK_ID}",
            json=get_camunda_task_mock(
                id=TASK_ID, process_instance_id=PROCESS_INSTANCE_ID
            ),
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
            json={"value": ZAAK_URL, "type": "String"},
        )
        m_get_zaak.return_value = Zaak(
            url=ZAAK_URL,
            identificatie="0001",
            bronorganisatie="123456782",
            omschrijving="",
            toelichting="",
            zaaktype="https://open-zaak.nl/catalogi/api/v1/zaaktypen/123",
            registratiedatum=date.today(),
            startdatum=date.today(),
            einddatum=None,
            einddatum_gepland=None,
            uiterlijke_einddatum_afdoening=None,
            publicatiedatum=None,
            vertrouwelijkheidaanduiding="openbaar",
            status="",
            resultaat="",
            relevante_andere_zaken=[],
            zaakgeometrie={},
        )

        response = self.client.post(
            self.url,
            {"task_id": TASK_ID},
            HTTP_REFERER="http://testserver/",
        )

        self.assertEqual(response.status_code, 403)
