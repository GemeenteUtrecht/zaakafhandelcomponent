from django.test import TestCase
from django.urls import reverse

import requests_mock
from django_camunda.models import CamundaConfig
from rest_framework import status

from zac.accounts.tests.factories import UserFactory

ZAAK_URL = "https://some.zrc.nl/api/v1/zaken/a955573e-ce3f-4cf3-8ae0-87853d61f47a"
CAMUNDA_ROOT = "https://some.camunda.nl/"
CAMUNDA_API_PATH = "engine-rest/"
CAMUNDA_URL = f"{CAMUNDA_ROOT}{CAMUNDA_API_PATH}"


@requests_mock.Mocker()
class ProcessInstanceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        config = CamundaConfig.get_solo()
        config.root_url = CAMUNDA_ROOT
        config.rest_api_path = CAMUNDA_API_PATH
        config.save()

        cls.user = UserFactory.create()

    def setUp(self) -> None:
        super().setUp()
        self.client.force_login(self.user)

    def _setUpMock(self, m):
        self.data = [
            {
                "id": "205eae6b-d26f-11ea-86dc-e22fafe5f405",
                "definitionId": "42d15947-d17b-11ea-86dc-e22fafe5f405",
            },
            {
                "id": "905abd5f-d26f-11ea-86dc-e22fafe5f405",
                "definitionId": "accorderen:8:c76c8200-c766-11ea-86dc-e22fafe5f405",
            },
            {
                "id": "010fe90d-c122-11ea-a817-b6551116eb32",
                "definitionId": "Bezwaar-indienen:4:dc4baee3-c116-11ea-a817-b6551116eb32",
            },
        ]

        m.get(
            f"{CAMUNDA_URL}process-instance?variables=zaakUrl_eq_{ZAAK_URL}",
            json=[self.data[0]],
        )
        m.get(
            f"{CAMUNDA_URL}process-instance?superProcessInstance={self.data[0]['id']}",
            json=[self.data[1]],
        )
        m.get(
            f"{CAMUNDA_URL}process-instance?superProcessInstance={self.data[1]['id']}",
            json=[self.data[2]],
        )
        m.get(
            f"{CAMUNDA_URL}process-instance?superProcessInstance={self.data[2]['id']}",
            json=[],
        )

    def test_fetch_process_instances(self, m):
        self._setUpMock(m)

        url = reverse("camunda:fetch-process-instances")

        response = self.client.get(url, {"zaak_url": ZAAK_URL})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(
            data,
            [
                {
                    "id": self.data[0]["id"],
                    "definition_id": self.data[0]["definitionId"],
                    "sub_processes": [
                        {
                            "id": self.data[1]["id"],
                            "definition_id": self.data[1]["definitionId"],
                            "sub_processes": [
                                {
                                    "id": self.data[2]["id"],
                                    "definition_id": self.data[2]["definitionId"],
                                    "sub_processes": [],
                                }
                            ],
                        }
                    ],
                }
            ],
        )
