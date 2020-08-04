from datetime import date
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse_lazy

import requests_mock

from zac.accounts.tests.factories import SuperUserFactory, UserFactory
from zgw.models import Zaak


@requests_mock.Mocker()
class BPMNMessageSendTests(TestCase):
    url = reverse_lazy("core:send-message")

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = SuperUserFactory.create()

    def setUp(self):
        super().setUp()
        self.client.force_login(user=self.user)

    @patch("zac.core.views.processes._client_from_url")
    @patch("zac.core.views.processes.send_message")
    @patch("zac.core.views.processes.get_zaak")
    @patch("zac.core.views.processes.get_messages", return_value=["dummy"])
    def test_send_valid_message(
        self, m, m_get_messages, m_get_zaak, mock_send_message, *other_mocks
    ):
        PROCESS_INSTANCE_ID = "proces:1:f0a2e2c4-b35c-49f1-9fba-aaa7a161f247"
        ZAAK_URL = "https://open-zaak.nl/zaken/api/v1/zaken/1234"
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
            {"process_instance_id": PROCESS_INSTANCE_ID, "message": "dummy",},
            HTTP_REFERER="http://testserver/",
        )

        self.assertEqual(response.status_code, 302)

    @patch("zac.core.views.processes.get_messages", return_value=["wrong-message"])
    def test_send_invalid_message(self, m, m_get_messages):
        PROCESS_INSTANCE_ID = "proces:1:f0a2e2c4-b35c-49f1-9fba-aaa7a161f247"
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

        response = self.client.post(
            self.url,
            {"process_instance_id": PROCESS_INSTANCE_ID, "message": "dummy",},
            HTTP_REFERER="http://testserver/",
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response,
            "form",
            "message",
            ["Selecteer een geldige keuze. dummy is geen beschikbare keuze."],
        )

    @patch("zac.core.views.processes.send_message")
    @patch("zac.core.views.processes.get_zaak")
    @patch("zac.core.views.processes.get_messages", return_value=["dummy"])
    def test_no_permissions(self, m, m_get_messages, m_get_zaak, mock_send_message):
        user = UserFactory.create()
        self.client.force_login(user=user)

        PROCESS_INSTANCE_ID = "proces:1:f0a2e2c4-b35c-49f1-9fba-aaa7a161f247"
        ZAAK_URL = "https://open-zaak.nl/zaken/api/v1/zaken/1234"
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
            {"process_instance_id": PROCESS_INSTANCE_ID, "message": "dummy",},
            HTTP_REFERER="http://testserver/",
        )

        self.assertEqual(response.status_code, 403)
        mock_send_message.assert_not_called()

    def test_process_instance_does_not_exist(self, m):
        PROCESS_INSTANCE_ID = "proces:1:f0a2e2c4-b35c-49f1-9fba-aaa7a161f247"
        m.get(
            f"https://camunda.example.com/engine-rest/process-instance/{PROCESS_INSTANCE_ID}",
            status_code=404,
        )

        response = self.client.post(
            self.url,
            {"process_instance_id": PROCESS_INSTANCE_ID, "message": "dummy",},
            HTTP_REFERER="http://testserver/",
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response,
            "form",
            "message",
            ["Selecteer een geldige keuze. dummy is geen beschikbare keuze."],
        )
