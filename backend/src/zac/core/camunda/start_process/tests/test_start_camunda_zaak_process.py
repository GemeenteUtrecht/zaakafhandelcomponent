from unittest.mock import patch

from django.urls import reverse

import requests_mock
from django_camunda.models import CamundaConfig
from requests.exceptions import HTTPError
from rest_framework import status
from rest_framework.test import APITestCase, APITransactionTestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import (
    BlueprintPermissionFactory,
    SuperUserFactory,
    UserFactory,
)
from zac.core.permissions import zaakprocess_starten, zaken_inzien
from zac.core.tests.utils import ClearCachesMixin
from zac.tests.utils import mock_resource_get
from zgw.models.zrc import Zaak

from .factories import CamundaStartProcessFactory

DOCUMENTS_ROOT = "http://documents.nl/api/v1/"
ZAKEN_ROOT = "http://zaken.nl/api/v1/"
CATALOGI_ROOT = "https://open-zaak.nl/catalogi/api/v1/"
ZAAK_URL = "https://some.zrc.nl/api/v1/zaken/a955573e-ce3f-4cf3-8ae0-87853d61f47a"
CAMUNDA_ROOT = "https://camunda.example.com/"
CAMUNDA_API_PATH = "engine-rest/"
CAMUNDA_URL = f"{CAMUNDA_ROOT}{CAMUNDA_API_PATH}"


# Taken from https://docs.camunda.org/manual/7.13/reference/rest/history/task/get-task-query/
COMPLETED_TASK_DATA = {
    "id": "1790e564-8b57-11ec-baad-6ed7f836cf1f",
    "processDefinitionKey": "HARVO_behandelen",
    "processDefinitionId": "HARVO_behandelen:61:54586277-7922-11ec-8209-aa9470edda89",
    "processInstanceId": "0df2bc16-8b57-11ec-baad-6ed7f836cf1f",
    "executionId": "0df2bc16-8b57-11ec-baad-6ed7f836cf1f",
    "caseDefinitionKey": None,
    "caseDefinitionId": None,
    "caseInstanceId": None,
    "caseExecutionId": None,
    "activityInstanceId": "Activity_0bkealj:1790e563-8b57-11ec-baad-6ed7f836cf1f",
    "name": "Inhoudelijk voorbereiden (= checkvragen)",
    "description": None,
    "deleteReason": "completed",
    "owner": None,
    "assignee": "some-user",
    "startTime": "2022-02-11T16:24:31.545+0000",
    "endTime": "2022-02-11T16:24:43.006+0000",
    "duration": 11461,
    "taskDefinitionKey": "Activity_0bkealj",
    "priority": 50,
    "due": None,
    "parentTaskId": None,
    "followUp": None,
    "tenantId": None,
    "removalTime": None,
    "rootProcessInstanceId": "0df2bc16-8b57-11ec-baad-6ed7f836cf1f",
}

PROCESS_DEFINITION = {
    "id": f"start_camunda_process:8:c76c8200-c766-11ea-86dc-e22fafe5f405",
    "key": "start_camunda_process",
    "category": "http://bpmn.io/schema/bpmn",
    "description": None,
    "name": "Start Camunda Process",
    "version": 8,
    "resource": "start_camunda_process.bpmn",
    "deployment_id": "c76a10fd-c766-11ea-86dc-e22fafe5f405",
    "diagram": None,
    "suspended": False,
    "tenant_id": None,
    "version_tag": None,
    "history_time_to_live": None,
    "startable_in_tasklist": True,
}

PROCESS_INSTANCE = {
    "id": "205eae6b-d26f-11ea-86dc-e22fafe5f405",
    "definitionId": PROCESS_DEFINITION["id"],
    "businessKey": "",
    "caseInstanceId": "",
    "suspended": False,
    "tenantId": "",
}


@requests_mock.Mocker()
class StartCamundaProcessViewTests(ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        config = CamundaConfig.get_solo()
        config.root_url = CAMUNDA_ROOT
        config.rest_api_path = CAMUNDA_API_PATH
        config.save()
        cls.user = SuperUserFactory.create(username="some-user")
        cls.endpoint = reverse(
            "start-process",
            kwargs={
                "bronorganisatie": "123456782",
                "identificatie": "ZAAK-2020-0010",
            },
        )

        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)

        catalogus_url = (
            f"{CATALOGI_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            catalogus=catalogus_url,
            url=f"{CATALOGI_ROOT}zaaktypen/4f622c65-5ffe-476e-96ee-f0710bd0c92b",
        )
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            id="30a98ef3-bf35-4287-ac9c-fed048619dd7",
            url=f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7",
            zaaktype=cls.zaaktype["url"],
        )
        cls.zaak_obj = factory(Zaak, cls.zaak)
        cls.zaak_obj.zaaktype = factory(ZaakType, cls.zaaktype)

        cls.camunda_start_process = CamundaStartProcessFactory.create(
            zaaktype_identificatie=cls.zaaktype["identificatie"],
            zaaktype_catalogus=cls.zaaktype["catalogus"],
            process_definition_key=PROCESS_DEFINITION["key"],
        )

    def setUp(self) -> None:
        super().setUp()
        self.client.force_authenticate(self.user)

    def test_success_start_camunda_process(self, m):
        m.get(
            f"{CAMUNDA_URL}process-instance?variables=zaakUrl_eq_{self.zaak['url']}",
            json=[PROCESS_INSTANCE],
        )
        m.get(
            f"{CAMUNDA_URL}process-instance?superProcessInstance={PROCESS_INSTANCE['id']}",
            json=[],
        )
        m.get(
            f"{CAMUNDA_URL}process-definition?processDefinitionIdIn={PROCESS_DEFINITION['id']}",
            json=[PROCESS_DEFINITION],
        )
        m.post(
            f"{CAMUNDA_URL}process-definition/key/{PROCESS_DEFINITION['key']}/start",
            status_code=201,
            json={
                "links": [{"rel": "self", "href": "https://some-url.com/"}],
                "id": PROCESS_INSTANCE["id"],
            },
        )

        with patch(
            "zac.core.camunda.start_process.views.StartCamundaProcessView.get_object",
            return_value=self.zaak_obj,
        ):
            response = self.client.post(self.endpoint, {})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.json(),
            {
                "instanceId": PROCESS_INSTANCE["id"],
                "instanceUrl": "https://some-url.com/",
            },
        )
        self.assertEqual(
            m.last_request.url,
            f"{CAMUNDA_URL}process-definition/key/{PROCESS_DEFINITION['key']}/start",
        )

        self.assertEqual(
            m.last_request.json(),
            {
                "businessKey": "",
                "withVariablesInReturn": False,
                "variables": {
                    "zaakUrl": self.zaak["url"],
                    "zaakIdentificatie": self.zaak["identificatie"],
                    "zaakDetails": {
                        "omschrijving": self.zaak["omschrijving"],
                        "zaaktypeOmschrijving": self.zaaktype["omschrijving"],
                    },
                },
            },
        )

    def test_start_camunda_process_no_process_instance_to_close(self, m):
        m.get(
            f"{CAMUNDA_URL}process-instance?variables=zaakUrl_eq_{self.zaak['url']}",
            json=[],
        )
        m.post(
            f"{CAMUNDA_URL}process-definition/key/{PROCESS_DEFINITION['key']}/start",
            status_code=201,
            json={
                "links": [{"rel": "self", "href": "https://some-url.com/"}],
                "id": PROCESS_INSTANCE["id"],
            },
        )

        with patch(
            "zac.core.camunda.start_process.views.StartCamundaProcessView.get_object",
            return_value=self.zaak_obj,
        ):
            response = self.client.post(self.endpoint, {})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.json(),
            {
                "instanceId": PROCESS_INSTANCE["id"],
                "instanceUrl": "https://some-url.com/",
            },
        )

    def test_start_camunda_process_no_process_definition_found(self, m):
        m.get(
            f"{CAMUNDA_URL}process-instance?variables=zaakUrl_eq_{self.zaak['url']}",
            json=[PROCESS_INSTANCE],
        )
        m.get(
            f"{CAMUNDA_URL}process-instance?superProcessInstance={PROCESS_INSTANCE['id']}",
            json=[],
        )
        m.get(
            f"{CAMUNDA_URL}process-definition?processDefinitionIdIn={PROCESS_DEFINITION['id']}",
            json=[],
        )
        m.post(
            f"{CAMUNDA_URL}process-definition/key/{PROCESS_DEFINITION['key']}/start",
            status_code=201,
            json={
                "links": [{"rel": "self", "href": "https://some-url.com/"}],
                "id": PROCESS_INSTANCE["id"],
            },
        )

        with patch(
            "zac.core.camunda.start_process.views.StartCamundaProcessView.get_object",
            return_value=self.zaak_obj,
        ):
            response = self.client.post(self.endpoint, {})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.json(),
            {
                "instanceId": PROCESS_INSTANCE["id"],
                "instanceUrl": "https://some-url.com/",
            },
        )


@requests_mock.Mocker()
class StartCamundaProcessViewPermissionTests(ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        config = CamundaConfig.get_solo()
        config.root_url = CAMUNDA_ROOT
        config.rest_api_path = CAMUNDA_API_PATH
        config.save()
        cls.endpoint = reverse(
            "start-process",
            kwargs={
                "bronorganisatie": "123456782",
                "identificatie": "ZAAK-2020-0010",
            },
        )

        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)

        catalogus_url = (
            f"{CATALOGI_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            catalogus=catalogus_url,
            url=f"{CATALOGI_ROOT}zaaktypen/4f622c65-5ffe-476e-96ee-f0710bd0c92b",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.beperkt_openbaar,
            omschrijving="ZT1",
        )
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            id="30a98ef3-bf35-4287-ac9c-fed048619dd7",
            url=f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7",
            zaaktype=cls.zaaktype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.beperkt_openbaar,
        )
        cls.zaak_obj = factory(Zaak, cls.zaak)
        cls.zaak_obj.zaaktype = factory(ZaakType, cls.zaaktype)

        cls.camunda_start_process = CamundaStartProcessFactory.create(
            zaaktype_identificatie=cls.zaaktype["identificatie"],
            zaaktype_catalogus=cls.zaaktype["catalogus"],
            process_definition_key=PROCESS_DEFINITION["key"],
        )
        cls.find_zaak_patcher = patch(
            "zac.core.camunda.start_process.views.StartCamundaProcessView.get_object",
            return_value=cls.zaak_obj,
        )

    def setUp(self) -> None:
        super().setUp()
        self.user = UserFactory.create()
        self.client.force_authenticate(self.user)
        self.find_zaak_patcher.start()
        self.addCleanup(self.find_zaak_patcher.stop)

    def test_no_permissions(self, m):
        with patch(
            "zac.core.camunda.start_process.views.StartCamundaProcessView.get_object",
            return_value=self.zaak_obj,
        ):
            response = self.client.post(self.endpoint, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_perm_but_not_for_zaaktype(self, m):
        # gives them access to the page, but no catalogus specified -> nothing visible
        BlueprintPermissionFactory.create(
            role__permissions=[zaakprocess_starten.name],
            for_user=self.user,
            policy={
                "catalogus": "",
                "zaaktype_omschrijving": "",
                "max_va": VertrouwelijkheidsAanduidingen.beperkt_openbaar,
            },
        )
        with patch(
            "zac.core.camunda.start_process.views.StartCamundaProcessView.get_object",
            return_value=self.zaak_obj,
        ):
            response = self.client.post(self.endpoint, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_perm_but_not_for_va(self, m):
        # gives them access to the page, but no catalogus specified -> nothing visible
        BlueprintPermissionFactory.create(
            role__permissions=[zaakprocess_starten.name],
            for_user=self.user,
            policy={
                "catalogus": "",
                "zaaktype_omschrijving": "",
                "max_va": VertrouwelijkheidsAanduidingen.openbaar,
            },
        )
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_perm(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.zaaktype)
        # gives them access to the page, zaaktype and VA specified -> visible
        BlueprintPermissionFactory.create(
            role__permissions=[zaakprocess_starten.name],
            for_user=self.user,
            policy={
                "catalogus": self.zaaktype["catalogus"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            },
        )
        m.get(
            f"{CAMUNDA_URL}process-instance?variables=zaakUrl_eq_{self.zaak['url']}",
            json=[PROCESS_INSTANCE],
        )
        m.get(
            f"{CAMUNDA_URL}process-instance?superProcessInstance={PROCESS_INSTANCE['id']}",
            json=[],
        )
        m.get(
            f"{CAMUNDA_URL}process-definition?processDefinitionIdIn={PROCESS_DEFINITION['id']}",
            json=[PROCESS_DEFINITION],
        )
        m.post(
            f"{CAMUNDA_URL}process-definition/key/{PROCESS_DEFINITION['key']}/start",
            status_code=201,
            json={
                "links": [{"rel": "self", "href": "https://some-url.com/"}],
                "id": PROCESS_INSTANCE["id"],
            },
        )
        response = self.client.post(self.endpoint, {})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
