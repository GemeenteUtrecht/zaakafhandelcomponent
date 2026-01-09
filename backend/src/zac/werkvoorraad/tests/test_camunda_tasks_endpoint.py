from unittest.mock import patch

from django.urls import reverse

import requests_mock
from django_camunda.utils import underscoreize
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from zac.accounts.tests.factories import GroupFactory, SuperUserFactory, UserFactory
from zac.camunda.data import Task
from zac.elasticsearch.tests.utils import ESMixin
from zac.tests.compat import generate_oas_component, mock_service_oas_get
from zac.tests.utils import mock_resource_get

# Taken from https://docs.camunda.org/manual/7.13/reference/rest/task/get/
TASK_DATA = {
    "id": "598347ee-62fc-46a2-913a-6e0788bc1b8c",
    "name": "aName",
    "assignee": None,
    "created": "2013-01-23T13:42:42Z",
    "due": "2013-01-23T13:49:42.576+0200",
    "followUp": "2013-01-23T13:44:42.437+0200",
    "delegationState": "RESOLVED",
    "description": "aDescription",
    "executionId": "anExecution",
    "owner": "anOwner",
    "parentTaskId": None,
    "priority": 42,
    "processDefinitionId": "aProcDefId",
    "processInstanceId": "87a88170-8d5c-4dec-8ee2-972a0be1b564",
    "caseDefinitionId": "aCaseDefId",
    "caseInstanceId": "aCaseInstId",
    "caseExecutionId": "aCaseExecution",
    "taskDefinitionKey": "aTaskDefinitionKey",
    "suspended": False,
    "formKey": "",
    "tenantId": "aTenantId",
}

ZAKEN_ROOT = "http://zaken.nl/api/v1/"
CATALOGI_ROOT = "http://catalogus.nl/api/v1/"
CATALOGI_URL = f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"


def _get_task(**overrides):
    data = underscoreize({**TASK_DATA, **overrides})
    return factory(Task, data)


@requests_mock.Mocker()
class CamundaTasksTests(ESMixin, APITestCase):
    """
    Test the camunda tasks workstack API endpoints.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.groups = GroupFactory.create_batch(2)
        cls.group_endpoint = reverse("werkvoorraad:group-tasks")
        cls.user = SuperUserFactory.create()
        cls.user.groups.set(cls.groups)
        cls.user_endpoint = reverse(
            "werkvoorraad:user-tasks",
        )

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        cls.catalogus = generate_oas_component(
            "ztc",
            "schemas/Catalogus",
            url=CATALOGI_URL,
            domein="DOME",
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            omschrijving="ZT1",
            catalogus=CATALOGI_URL,
        )
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            identificatie="ZAAK-2020-0010",
            bronorganisatie="123456782",
            startdatum="2021-02-12",
            einddatum=None,
            einddatumGepland=None,
            uiterlijkeEinddatumAfdoening="2021-02-17",
            zaaktype=cls.zaaktype["url"],
        )
        cls.task = _get_task(**{"assignee": cls.user})

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    def _setUpMock(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        zaak_document = self.create_zaak_document(self.zaak)
        zaak_document.zaaktype = self.create_zaaktype_document(self.zaaktype)
        zaak_document.save()
        self.refresh_index()

    def test_other_user_logging_in(self, m):
        self._setUpMock(m)
        # Sanity check
        self.client.logout()
        user = UserFactory.create()
        self.client.force_authenticate(user=user)
        with patch(
            "zac.werkvoorraad.views.get_zaak_urls_from_tasks",
            return_value={},
        ):
            with patch(
                "zac.werkvoorraad.views.get_camunda_user_tasks_for_assignee",
                return_value=[],
            ):
                response = self.client.get(self.user_endpoint)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"], [])

    def test_user_tasks_endpoint(self, m):
        self._setUpMock(m)
        with patch(
            "zac.werkvoorraad.views.get_zaak_urls_from_tasks",
            return_value={self.task.id: self.zaak["url"]},
        ):
            with patch(
                "zac.werkvoorraad.views.get_camunda_user_tasks_for_assignee",
                return_value=[self.task],
            ):
                response = self.client.get(self.user_endpoint)

        self.assertEqual(response.status_code, 200)
        data = response.json()["results"]
        self.assertEqual(
            data,
            [
                {
                    "task": TASK_DATA["name"],
                    "zaak": {
                        "identificatie": self.zaak["identificatie"],
                        "bronorganisatie": self.zaak["bronorganisatie"],
                        "url": self.zaak["url"],
                        "status": {
                            "datumStatusGezet": None,
                            "statustoelichting": None,
                            "statustype": None,
                            "url": None,
                        },
                        "zaaktype": {
                            "url": self.zaaktype["url"],
                            "catalogus": self.zaaktype["catalogus"],
                            "catalogusDomein": self.catalogus["domein"],
                            "omschrijving": self.zaaktype["omschrijving"],
                            "identificatie": self.zaaktype["identificatie"],
                        },
                        "omschrijving": self.zaak["omschrijving"],
                        "deadline": "2021-02-17T00:00:00Z",
                    },
                },
            ],
        )

    def test_group_tasks_endpoint(self, m):
        self._setUpMock(m)
        with patch(
            "zac.werkvoorraad.views.get_zaak_urls_from_tasks",
            return_value={self.task.id: self.zaak["url"]},
        ):
            with patch(
                "zac.werkvoorraad.views.get_camunda_user_tasks_for_user_groups",
                return_value=[_get_task(**{"assignee": self.groups[0]})],
            ):
                response = self.client.get(self.group_endpoint)

        self.assertEqual(response.status_code, 200)
        data = response.json()["results"]
        self.assertEqual(
            data,
            [
                {
                    "task": TASK_DATA["name"],
                    "zaak": {
                        "identificatie": self.zaak["identificatie"],
                        "bronorganisatie": self.zaak["bronorganisatie"],
                        "url": self.zaak["url"],
                        "status": {
                            "datumStatusGezet": None,
                            "statustoelichting": None,
                            "statustype": None,
                            "url": None,
                        },
                        "zaaktype": {
                            "url": self.zaaktype["url"],
                            "catalogus": self.zaaktype["catalogus"],
                            "catalogusDomein": self.catalogus["domein"],
                            "omschrijving": self.zaaktype["omschrijving"],
                            "identificatie": self.zaaktype["identificatie"],
                        },
                        "omschrijving": self.zaak["omschrijving"],
                        "deadline": "2021-02-17T00:00:00Z",
                    },
                },
            ],
        )

    def test_group_tasks_endpoint_no_groups(self, m):
        self._setUpMock(m)
        user = UserFactory.create()
        self.client.force_authenticate(user)
        with patch(
            "zac.werkvoorraad.views.get_zaak_urls_from_tasks",
            return_value={self.task.id: self.zaak["url"]},
        ):
            response = self.client.get(self.group_endpoint)

        self.assertEqual(response.status_code, 200)
        data = response.json()["results"]
        self.assertEqual(
            data,
            [],
        )

    def test_user_tasks_endpoint_zaak_cant_be_found(self, m):
        self._setUpMock(m)
        with patch(
            "zac.werkvoorraad.views.get_zaak_urls_from_tasks",
            return_value={self.task.id: self.zaak["url"]},
        ):
            with patch(
                "zac.werkvoorraad.views.get_camunda_user_tasks_for_assignee",
                return_value=[self.task],
            ):
                with patch(
                    "zac.werkvoorraad.views.search_zaken",
                    return_value=[],
                ):
                    response = self.client.get(self.user_endpoint)
        self.assertEqual(response.status_code, 200)
        data = response.json()["results"]
        self.assertEqual(data, [])
