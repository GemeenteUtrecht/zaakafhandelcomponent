from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _

import requests_mock
from django_camunda.client import get_client
from django_camunda.models import CamundaConfig
from django_camunda.utils import serialize_variable
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import GroupFactory, SuperUserFactory, UserFactory
from zac.core.tests.utils import ClearCachesMixin, mock_parallel
from zac.tests.utils import mock_resource_get

ZAKEN_ROOT = "https://some.zrc.nl/api/v1/"
ZAAK_URL = f"{ZAKEN_ROOT}zaken/a955573e-ce3f-4cf3-8ae0-87853d61f47a"
CAMUNDA_ROOT = "https://some.camunda.nl/"
CAMUNDA_API_PATH = "engine-rest/"
CAMUNDA_URL = f"{CAMUNDA_ROOT}{CAMUNDA_API_PATH}"
CREATE_ZAAK_PROCESS_DEFINITION_KEY = "zaak_aanmaken"


def _get_camunda_client():
    config = CamundaConfig.get_solo()
    config.root_url = CAMUNDA_ROOT
    config.rest_api_path = CAMUNDA_API_PATH
    config.save()
    return get_client()


@patch(
    "zac.camunda.process_instances.get_messages",
    return_value=["Annuleer behandeling", "Advies vragen"],
)
@override_settings(
    CREATE_ZAAK_PROCESS_DEFINITION_KEY=CREATE_ZAAK_PROCESS_DEFINITION_KEY
)
@requests_mock.Mocker()
class ProcessInstanceTests(ClearCachesMixin, APITestCase):
    url = reverse_lazy("fetch-process-instances")

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory.create()
        cls.group = GroupFactory.create()

    def setUp(self) -> None:
        super().setUp()
        self.client.force_authenticate(self.user)
        patchers = [
            patch("django_camunda.api.get_client", return_value=_get_camunda_client()),
        ]
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_fetch_zaak_url_from_process_instance(self, m_messages, m_request):
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        mock_service_oas_get(m_request, ZAKEN_ROOT, "zrc")

        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=ZAAK_URL,
        )
        mock_resource_get(m_request, zaak)

        m_request.get(
            f"{CAMUNDA_URL}process-instance/205eae6b-d26f-11ea-86dc-e22fafe5f405",
            json={
                "id": "205eae6b-d26f-11ea-86dc-e22fafe5f405",
                "definitionId": "Aanvraag_behandelen:8:c76c8200-c766-11ea-86dc-e22fafe5f405",
                "businessKey": "",
                "caseInstanceId": "",
                "suspended": False,
                "tenantId": "",
            },
        )
        m_request.get(
            f"{CAMUNDA_URL}process-instance/205eae6b-d26f-11ea-86dc-e22fafe5f405/variables/zaakDetailUrl?deserializeValue=false",
            json=serialize_variable("https://some-frontend-url.utrecht.nl/"),
        )
        m_request.get(
            f"{CAMUNDA_URL}process-instance/205eae6b-d26f-11ea-86dc-e22fafe5f405/variables/zaakUrl?deserializeValue=false",
            json=serialize_variable(ZAAK_URL),
        )
        url = reverse(
            "create-zaak-redirect-check",
            kwargs={"id": "205eae6b-d26f-11ea-86dc-e22fafe5f405"},
        )
        superuser = SuperUserFactory.create()
        self.client.force_authenticate(superuser)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "bronorganisatie": zaak["bronorganisatie"],
                "identificatie": zaak["identificatie"],
                "url": ZAAK_URL,
            },
        )
