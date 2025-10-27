from unittest.mock import patch

from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

import requests_mock
from django_camunda.client import get_client
from django_camunda.models import CamundaConfig
from rest_framework import status
from rest_framework.test import APITestCase

from zac.accounts.tests.factories import GroupFactory, UserFactory

from ..user_tasks.api import get_camunda_user_task_count

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
class CountTasksTests(APITestCase):
    url = reverse_lazy("count-tasks")

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory.create()
        cls.group = GroupFactory.create()

    def setUp(self) -> None:
        super().setUp()
        self.client.force_authenticate(self.user)
        patchers = [
            patch(
                "zac.camunda.user_tasks.api.get_client",
                return_value=_get_camunda_client(),
            ),
        ]
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_not_logged_in(self, m_request):
        self.client.logout()
        response = self.client.get(self.url, {"zaakUrl": ZAAK_URL})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_count_tasks(self, m_request):
        data = {"count": 420}
        m_request.post(
            f"{CAMUNDA_URL}task/count",
            json=data,
        )

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {"count": 420})

    def test_count_tasks_no_assignees(self, m_request):
        count = get_camunda_user_task_count([])
        self.assertEqual(count, 0)
