import uuid
from unittest.mock import patch

from django.urls import reverse

import requests_mock
from rest_framework import exceptions, status
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import BlueprintPermissionFactory, UserFactory
from zac.camunda.data import Task
from zac.core.models import CoreConfig
from zac.core.permissions import zaakproces_usertasks
from zac.tests.utils import mock_resource_get
from zgw.models.zrc import Zaak

from ..api.serializers import SetTaskAssigneeSerializer

CATALOGI_ROOT = "http://catalogus.nl/api/v1/"
ZAKEN_ROOT = "http://zaken.nl/api/v1/"

TASK_DATA = {
    "id": "598347ee-62fc-46a2-913a-6e0788bc1b8c",
    "name": "aName",
    "assignee": None,
    "created": "2013-01-23T13:42:42.000+0200",
    "due": "2013-01-23T13:49:42.576+0200",
    "follow_up": "2013-01-23T13:44:42.437+0200",
    "delegation_state": "RESOLVED",
    "description": "aDescription",
    "execution_id": "anExecution",
    "owner": "anOwner",
    "parent_task_id": None,
    "priority": 42,
    "process_definition_id": "aProcDefId",
    "process_instance_id": "87a88170-8d5c-4dec-8ee2-972a0be1b564",
    "case_definition_id": "aCaseDefId",
    "case_instance_id": "aCaseInstId",
    "case_execution_id": "aCaseExecution",
    "task_definition_key": "aTaskDefinitionKey",
    "suspended": False,
    "form_key": "",
    "tenant_id": "aTenantId",
}


class SetTaskAssigneeSerializerTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls._uuid = uuid.uuid4()
        cls.data = {
            "task": cls._uuid,
            "assignee": "some-user",
            "delegate": "some-delegate",
        }

        cls.task = factory(Task, TASK_DATA)

    @patch("zac.camunda.api.fields.get_task", return_value=None)
    def test_serializer_fail_validation(self, *mocks):
        serializer = SetTaskAssigneeSerializer(data=self.data)
        with self.assertRaises(exceptions.ValidationError) as exc:
            serializer.is_valid(raise_exception=True)

        self.assertEqual(
            exc.exception.detail["task"][0],
            "De taak met de gegeven `id` bestaat niet (meer).",
        )
        self.assertEqual(
            exc.exception.detail["assignee"][0],
            "Een gebruiker met `username` some-user bestaat niet. Een groep met `name` some-user bestaat niet.",
        )
        self.assertEqual(
            exc.exception.detail["delegate"][0],
            "Een gebruiker met `username` some-delegate bestaat niet. Een groep met `name` some-delegate bestaat niet.",
        )

    def test_serializer_success(self):
        users = UserFactory.create_batch(2)
        data = {
            **self.data,
            **{"assignee": users[0].username, "delegate": users[1].username},
        }

        serializer = SetTaskAssigneeSerializer(data=data)
        with patch("zac.camunda.api.fields.get_task", return_value=self.task):
            serializer.is_valid(raise_exception=True)


class SetTaskAssigneePermissionAndResponseTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.task = factory(Task, TASK_DATA)

        cls.patch_get_task = patch(
            "zac.camunda.api.fields.get_task",
            return_value=cls.task,
        )

        cls.patch_get_process_instance = patch(
            "zac.camunda.api.views.get_process_instance",
            return_value=None,
        )

        cls.patch_get_process_zaak_url = patch(
            "zac.camunda.api.views.get_process_zaak_url",
            return_value=None,
        )

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)

        catalogus_url = (
            f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=catalogus_url,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT1",
        )
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            identificatie="ZAAK-2020-0010",
            bronorganisatie="123456782",
            zaaktype=cls.zaaktype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.beperkt_openbaar,
            startdatum="2020-12-25",
            uiterlijkeEinddatumAfdoening="2021-01-04",
        )

        cls.patch_get_zaak = patch(
            "zac.camunda.api.views.get_zaak",
            return_value=factory(Zaak, zaak),
        )

        cls.patch_fetch_zaaktype = patch(
            "zac.camunda.api.views.fetch_zaaktype",
            return_value=factory(ZaakType, cls.zaaktype),
        )

        cls.endpoint = reverse("claim-task")

        cls.core_config = CoreConfig.get_solo()
        cls.core_config.app_id = "http://some-open-zaak-url.nl/with/uuid/"
        cls.core_config.save()

    def setUp(self):
        super().setUp()

        self.patch_get_process_instance.start()
        self.addCleanup(self.patch_get_process_instance.stop)

        self.patch_get_process_zaak_url.start()
        self.addCleanup(self.patch_get_process_zaak_url.stop)

        self.patch_get_zaak.start()
        self.addCleanup(self.patch_get_zaak.stop)

        self.patch_fetch_zaaktype.start()
        self.addCleanup(self.patch_fetch_zaaktype.stop)

    def test_not_authenticated(self):
        response = self.client.post(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_no_permissions(self):
        user = UserFactory.create()
        self.client.force_authenticate(user=user)

        response = self.client.post(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_has_perm_task_not_found(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        user = UserFactory.create()
        BlueprintPermissionFactory.create(
            role__permissions=[zaakproces_usertasks.name],
            for_user=user,
            policy={
                "catalogus": self.zaaktype["catalogus"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            },
        )

        self.client.force_authenticate(user=user)

        data = {
            "task": self.task.id,
            "assignee": user.username,
            "delegate": "",
        }

        with patch("zac.camunda.api.fields.get_task", return_value=None):
            response = self.client.post(
                self.endpoint,
                data=data,
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {"task": ["De taak met de gegeven `id` bestaat niet (meer)."]},
        )

    @requests_mock.Mocker()
    @patch("zac.camunda.api.views.SetTaskAssigneeView._create_rol", return_value=None)
    def test_has_perm_set_assignee_and_delegate(self, m, mock_create_rol):
        self.patch_get_task.start()
        self.addCleanup(self.patch_get_task.stop)

        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.zaaktype)
        user = UserFactory.create()
        BlueprintPermissionFactory.create(
            role__permissions=[zaakproces_usertasks.name],
            for_user=user,
            policy={
                "catalogus": self.zaaktype["catalogus"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            },
        )

        self.client.force_authenticate(user=user)

        m.post(
            f"https://camunda.example.com/engine-rest/task/{self.task.id}/assignee",
            status_code=204,
        )

        m.post(
            f"https://camunda.example.com/engine-rest/task/{self.task.id}/delegate",
            status_code=204,
        )

        data = {
            "task": self.task.id,
            "assignee": user.username,
            "delegate": "",
        }

        # data with assignee
        response = self.client.post(
            self.endpoint,
            data=data,
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        expected_payload = {"userId": f"user:{user.username}"}
        self.assertEqual(m.last_request.json(), expected_payload)
        self.assertIn("assignee", m.last_request.url)

        # data with delegate
        data.update({"assignee": "", "delegate": user.username})
        response = self.client.post(
            self.endpoint,
            data=data,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(m.last_request.json(), expected_payload)
        self.assertIn("delegate", m.last_request.url)
