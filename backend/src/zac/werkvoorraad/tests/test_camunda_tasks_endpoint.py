from unittest.mock import patch

from django.urls import reverse

from django_camunda.utils import underscoreize
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component

from zac.accounts.tests.factories import GroupFactory, SuperUserFactory, UserFactory
from zac.camunda.data import Task
from zac.elasticsearch.tests.utils import ESMixin

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


def _get_task(**overrides):
    data = underscoreize({**TASK_DATA, **overrides})
    return factory(Task, data)


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
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            omschrijving="ZT1",
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
        zaak_document = self.create_zaak_document(self.zaak)
        zaak_document.zaaktype = self.create_zaaktype_document(self.zaaktype)
        zaak_document.save()
        self.refresh_index()

    def test_other_user_logging_in(self):
        # Sanity check
        self.client.logout()
        user = UserFactory.create()
        self.client.force_authenticate(user=user)
        with patch(
            "zac.werkvoorraad.api.views.get_camunda_user_tasks",
            return_value=[],
        ):
            response = self.client.get(self.user_endpoint)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_user_tasks_endpoint(self):
        with patch(
            "zac.werkvoorraad.api.views.get_zaak_url_from_context",
            return_value=(self.task.id, self.zaak["url"]),
        ):
            with patch(
                "zac.werkvoorraad.api.views.get_camunda_user_tasks",
                return_value=[self.task],
            ):
                response = self.client.get(self.user_endpoint)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(
            data,
            [
                {
                    "task": {
                        "name": TASK_DATA["name"],
                        "assignee": {
                            "email": self.user.email,
                            "firstName": self.user.first_name,
                            "fullName": self.user.get_full_name(),
                            "id": self.user.id,
                            "isStaff": self.user.is_staff,
                            "lastName": self.user.last_name,
                            "username": self.user.username,
                            "groups": [group.name for group in self.groups],
                        },
                        "assigneeType": "user",
                        "created": TASK_DATA["created"],
                        "hasForm": False,
                        "id": TASK_DATA["id"],
                        "canCancelTask": False,
                    },
                    "zaak": {
                        "bronorganisatie": self.zaak["bronorganisatie"],
                        "identificatie": self.zaak["identificatie"],
                        "url": self.zaak["url"],
                        "status": {
                            "datumStatusGezet": None,
                            "statustoelichting": None,
                            "statustype": None,
                            "url": None,
                        },
                    },
                },
            ],
        )

    def test_group_tasks_endpoint(self):
        with patch(
            "zac.werkvoorraad.api.views.get_zaak_url_from_context",
            return_value=(self.task.id, self.zaak["url"]),
        ):
            with patch(
                "zac.werkvoorraad.api.views.get_camunda_group_tasks",
                return_value=[_get_task(**{"assignee": self.groups[0]})],
            ):
                response = self.client.get(self.group_endpoint)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(
            data,
            [
                {
                    "task": {
                        "name": TASK_DATA["name"],
                        "assignee": {
                            "id": self.groups[0].id,
                            "fullName": f"Groep: {self.groups[0].name}",
                            "name": self.groups[0].name,
                        },
                        "assigneeType": "group",
                        "created": TASK_DATA["created"],
                        "hasForm": False,
                        "id": TASK_DATA["id"],
                        "canCancelTask": False,
                    },
                    "zaak": {
                        "bronorganisatie": self.zaak["bronorganisatie"],
                        "identificatie": self.zaak["identificatie"],
                        "url": self.zaak["url"],
                        "status": {
                            "datumStatusGezet": None,
                            "statustoelichting": None,
                            "statustype": None,
                            "url": None,
                        },
                    },
                },
            ],
        )

    def test_user_tasks_endpoint_zaak_cant_be_found(self):
        with patch(
            "zac.werkvoorraad.api.views.get_zaak_url_from_context",
            return_value=(self.task.id, self.zaak["url"]),
        ):
            with patch(
                "zac.werkvoorraad.api.views.get_camunda_user_tasks",
                return_value=[self.task],
            ):
                with patch(
                    "zac.werkvoorraad.api.views.search",
                    return_value=[],
                ):
                    response = self.client.get(self.user_endpoint)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data, [])
