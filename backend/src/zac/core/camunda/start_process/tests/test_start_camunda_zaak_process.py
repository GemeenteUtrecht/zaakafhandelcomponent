import datetime
from copy import deepcopy
from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse

import requests_mock
from django_camunda.models import CamundaConfig
from django_camunda.utils import serialize_variable
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.api_models.constants import (
    RolOmschrijving,
    VertrouwelijkheidsAanduidingen,
)
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import (
    ApplicationTokenFactory,
    BlueprintPermissionFactory,
    SuperUserFactory,
    UserFactory,
)
from zac.core.models import CoreConfig, MetaObjectTypesConfig
from zac.core.permissions import zaakprocess_starten, zaken_geforceerd_bijwerken
from zac.core.tests.utils import ClearCachesMixin
from zac.tests.utils import mock_resource_get, paginated_response
from zgw.models.zrc import Zaak

from .utils import (
    CATALOGI_ROOT,
    OBJECTS_ROOT,
    OBJECTTYPES_ROOT,
    START_CAMUNDA_PROCESS_FORM,
    START_CAMUNDA_PROCESS_FORM_OBJ,
    START_CAMUNDA_PROCESS_FORM_OT,
    ZAKEN_ROOT,
)

ZAAK_URL = "https://some.zrc.nl/api/v1/zaken/a955573e-ce3f-4cf3-8ae0-87853d61f47a"
CAMUNDA_ROOT = "https://camunda.example.com/"
CAMUNDA_API_PATH = "engine-rest/"
CAMUNDA_URL = f"{CAMUNDA_ROOT}{CAMUNDA_API_PATH}"


# Taken from https://docs.camunda.org/manual/7.13/reference/rest/history/task/get-task-query/
COMPLETED_TASK_DATA = {
    "id": "1790e564-8b57-11ec-baad-6ed7f836cf1f",
    "processDefinitionKey": START_CAMUNDA_PROCESS_FORM["camundaProcessDefinitionKey"],
    "processDefinitionId": f"{START_CAMUNDA_PROCESS_FORM['camundaProcessDefinitionKey']}:8:c76c8200-c766-11ea-86dc-e22fafe5f405",
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
    "rootProcessInstanceId": "205eae6b-d26f-11ea-86dc-e22fafe5f405",
}

PROCESS_DEFINITION = {
    "id": f"{START_CAMUNDA_PROCESS_FORM['camundaProcessDefinitionKey']}:8:c76c8200-c766-11ea-86dc-e22fafe5f405",
    "key": START_CAMUNDA_PROCESS_FORM["camundaProcessDefinitionKey"],
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
        objecttypes_service = Service.objects.create(
            api_type=APITypes.ztc, api_root=OBJECTTYPES_ROOT
        )
        objects_service = Service.objects.create(
            api_type=APITypes.orc, api_root=OBJECTS_ROOT
        )
        meta_config = MetaObjectTypesConfig.get_solo()
        meta_config.start_camunda_process_form_objecttype = (
            START_CAMUNDA_PROCESS_FORM_OT["url"]
        )
        meta_config.save()
        core_config = CoreConfig.get_solo()
        core_config.primary_objects_api = objects_service
        core_config.primary_objecttypes_api = objecttypes_service
        core_config.save()
        catalogus_url = (
            f"{CATALOGI_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        )
        cls.catalogus = generate_oas_component(
            "ztc",
            "schemas/Catalogus",
            url=catalogus_url,
            domein=START_CAMUNDA_PROCESS_FORM["zaaktypeCatalogus"],
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            catalogus=catalogus_url,
            url=f"{CATALOGI_ROOT}zaaktypen/4f622c65-5ffe-476e-96ee-f0710bd0c92b",
            identificatie=START_CAMUNDA_PROCESS_FORM["zaaktypeIdentificaties"][0],
        )
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            id="30a98ef3-bf35-4287-ac9c-fed048619dd7",
            url=f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7",
            zaaktype=cls.zaaktype["url"],
            einddatum=None,
        )
        cls.zaak_obj = factory(Zaak, cls.zaak)
        cls.zaak_obj.zaaktype = factory(ZaakType, cls.zaaktype)

    def setUp(self) -> None:
        super().setUp()
        self.client.force_authenticate(self.user)

    def test_success_start_camunda_process(self, m):
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")
        m.get(
            f"{OBJECTTYPES_ROOT}objecttypes",
            json=paginated_response([START_CAMUNDA_PROCESS_FORM_OT]),
        )
        m.post(
            f"{OBJECTS_ROOT}objects/search",
            json=paginated_response([START_CAMUNDA_PROCESS_FORM_OBJ]),
        )
        mock_resource_get(m, self.catalogus)
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

        other_user = SuperUserFactory.create()
        for rt_omschrijving, user in [
            (RolOmschrijving.behandelaar, self.user),
            (RolOmschrijving.initiator, other_user),
        ]:
            with self.subTest("Testing roltypes initiator and behandelaar"):
                rol = generate_oas_component(
                    "zrc",
                    "schemas/Rol",
                    betrokkeneIdentificatie={"identificatie": f"user:{other_user}"},
                    betrokkeneType="medewerker",
                    omschrijvingGeneriek=rt_omschrijving,
                    betrokkene="",
                    indicatieMachtiging="gemachtigde",
                    zaak=self.zaak["url"],
                    url=f"{ZAKEN_ROOT}rollen/fb498b0b-e4c7-44f1-8e39-a55d9f55ebb8",
                )
                m.get(
                    f"{ZAKEN_ROOT}rollen?zaak={self.zaak_obj.url}",
                    json=paginated_response([rol]),
                )

                with patch(
                    "zac.core.camunda.start_process.views.StartCamundaProcessView.get_object",
                    return_value=self.zaak_obj,
                ):
                    response = self.client.post(self.endpoint, {})

                self.assertEqual(response.status_code, status.HTTP_200_OK)
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
                            "bptlAppId": serialize_variable(""),
                            "zaakUrl": serialize_variable(self.zaak["url"]),
                            "zaakIdentificatie": serialize_variable(
                                self.zaak["identificatie"]
                            ),
                            "zaakDetails": serialize_variable(
                                {
                                    "omschrijving": self.zaak["omschrijving"],
                                    "zaaktypeOmschrijving": self.zaaktype[
                                        "omschrijving"
                                    ],
                                }
                            ),
                            "initiator": serialize_variable(f"user:{user}"),
                        },
                    },
                )

    @patch("zac.core.camunda.start_process.views.get_rollen", return_value=[])
    def test_start_camunda_process_no_start_camunda_process_form_found(self, m, *mocks):
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")
        m.get(
            f"{OBJECTTYPES_ROOT}objecttypes",
            json=paginated_response([START_CAMUNDA_PROCESS_FORM_OT]),
        )
        m.post(f"{OBJECTS_ROOT}objects/search", json=paginated_response([]))
        mock_resource_get(m, self.catalogus)
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

        with patch(
            "zac.core.camunda.start_process.views.StartCamundaProcessView.get_object",
            return_value=self.zaak_obj,
        ):
            response = self.client.post(self.endpoint, {})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            response.json()["detail"],
            f"No start camunda process form found for zaaktype with `identificatie`: `{self.zaaktype['identificatie']}`.",
        )

    @patch("zac.core.camunda.start_process.views.get_rollen", return_value=[])
    def test_start_camunda_process_no_process_definition_found(self, m, *mocks):
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")
        m.get(
            f"{OBJECTTYPES_ROOT}objecttypes",
            json=paginated_response([START_CAMUNDA_PROCESS_FORM_OT]),
        )
        m.post(
            f"{OBJECTS_ROOT}objects/search",
            json=paginated_response([START_CAMUNDA_PROCESS_FORM_OBJ]),
        )
        mock_resource_get(m, self.catalogus)
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

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "instanceId": PROCESS_INSTANCE["id"],
                "instanceUrl": "https://some-url.com/",
            },
        )

    @patch("zac.core.camunda.start_process.views.get_rollen", return_value=[])
    def test_start_camunda_process_zaak_with_einddatum_and_running_process_instance(
        self, m, *mocks
    ):
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")
        m.get(
            f"{OBJECTTYPES_ROOT}objecttypes",
            json=paginated_response([START_CAMUNDA_PROCESS_FORM_OT]),
        )
        m.post(
            f"{OBJECTS_ROOT}objects/search",
            json=paginated_response([START_CAMUNDA_PROCESS_FORM_OBJ]),
        )
        mock_resource_get(m, self.catalogus)
        m.get(
            f"{CAMUNDA_URL}process-instance?variables=zaakUrl_eq_{self.zaak['url']}&processDefinitionKey={PROCESS_DEFINITION['key']}",
            json=[PROCESS_INSTANCE],
        )
        m.get(
            f"{CAMUNDA_URL}process-definition?processDefinitionIdIn={PROCESS_DEFINITION['id']}",
            json=[PROCESS_DEFINITION],
        )

        zaak_obj = deepcopy(self.zaak_obj)
        zaak_obj.einddatum = datetime.date(2020, 1, 1)
        with patch(
            "zac.core.camunda.start_process.views.StartCamundaProcessView.get_object",
            return_value=zaak_obj,
        ):
            response = self.client.post(self.endpoint, {})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "instanceId": PROCESS_INSTANCE["id"],
                "instanceUrl": f"{CAMUNDA_URL}process-instance/{PROCESS_INSTANCE['id']}",
            },
        )

    @override_settings(RESTART_ZAAK_PROCESS_DEFINITION_KEY="some-restart-key")
    @patch("zac.core.camunda.start_process.views.get_rollen", return_value=[])
    def test_start_camunda_process_zaak_with_einddatum_without_running_process_instance(
        self, m, *mocks
    ):
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")
        m.get(
            f"{OBJECTTYPES_ROOT}objecttypes",
            json=paginated_response([START_CAMUNDA_PROCESS_FORM_OT]),
        )
        m.post(
            f"{OBJECTS_ROOT}objects/search",
            json=paginated_response([START_CAMUNDA_PROCESS_FORM_OBJ]),
        )
        mock_resource_get(m, self.catalogus)
        m.get(
            f"{CAMUNDA_URL}process-instance?variables=zaakUrl_eq_{self.zaak['url']}&processDefinitionKey={PROCESS_DEFINITION['key']}",
            json=[],
        )
        m.get(
            f"{CAMUNDA_URL}process-definition?processDefinitionIdIn={PROCESS_DEFINITION['id']}",
            json=[],
        )

        m.post(
            f"{CAMUNDA_URL}process-definition/key/some-restart-key/start",
            status_code=201,
            json={
                "links": [{"rel": "self", "href": "https://some-url.com/"}],
                "id": PROCESS_INSTANCE["id"],
            },
        )

        zaak_obj = deepcopy(self.zaak_obj)
        zaak_obj.einddatum = datetime.date(2020, 1, 1)
        with patch(
            "zac.core.camunda.start_process.views.StartCamundaProcessView.get_object",
            return_value=zaak_obj,
        ):
            response = self.client.post(self.endpoint, {})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            m.last_request.url,
            f"{CAMUNDA_URL}process-definition/key/some-restart-key/start",
        )

        self.assertEqual(
            m.last_request.json(),
            {
                "businessKey": "",
                "withVariablesInReturn": False,
                "variables": {
                    "bptlAppId": {"type": "String", "value": ""},
                    "zaakUrl": {
                        "type": "String",
                        "value": zaak_obj.url,
                    },
                    "zaakIdentificatie": {
                        "type": "String",
                        "value": zaak_obj.identificatie,
                    },
                    "zaakDetails": serialize_variable(
                        {
                            "omschrijving": zaak_obj.omschrijving,
                            "zaaktypeOmschrijving": self.zaaktype["omschrijving"],
                        }
                    ),
                    "initiator": {"type": "String", "value": f"user:{self.user}"},
                },
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
        objects_service = Service.objects.create(
            api_type=APITypes.orc, api_root=OBJECTS_ROOT
        )
        objecttypes_service = Service.objects.create(
            api_type=APITypes.orc, api_root=OBJECTTYPES_ROOT
        )
        meta_config = MetaObjectTypesConfig.get_solo()
        meta_config.start_camunda_process_form_objecttype = (
            START_CAMUNDA_PROCESS_FORM_OT["url"]
        )
        meta_config.save()
        core_config = CoreConfig.get_solo()
        core_config.primary_objects_api = objects_service
        core_config.primary_objecttypes_api = objecttypes_service
        core_config.save()
        catalogus_url = (
            f"{CATALOGI_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        )
        cls.catalogus = generate_oas_component(
            "ztc",
            "schemas/Catalogus",
            url=catalogus_url,
            domein=START_CAMUNDA_PROCESS_FORM["zaaktypeCatalogus"],
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            catalogus=catalogus_url,
            url=f"{CATALOGI_ROOT}zaaktypen/4f622c65-5ffe-476e-96ee-f0710bd0c92b",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.beperkt_openbaar,
            omschrijving="ZT1",
            identificatie=START_CAMUNDA_PROCESS_FORM["zaaktypeIdentificaties"][0],
        )
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            id="30a98ef3-bf35-4287-ac9c-fed048619dd7",
            url=f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7",
            zaaktype=cls.zaaktype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.beperkt_openbaar,
            einddatum=None,
        )
        cls.zaak_obj = factory(Zaak, cls.zaak)
        cls.zaak_obj.zaaktype = factory(ZaakType, cls.zaaktype)
        cls.find_zaak_patcher = patch(
            "zac.core.camunda.start_process.views.StartCamundaProcessView.get_object",
            return_value=cls.zaak_obj,
        )

    def setUp(self) -> None:
        super().setUp()
        self.user = UserFactory.create()
        self.client.force_authenticate(self.user)

    def test_no_permissions(self, m):
        response = self.client.post(self.endpoint, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_perm_but_not_for_zaaktype(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
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
        with self.find_zaak_patcher:
            response = self.client.post(self.endpoint, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_perm_but_not_for_va(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)

        BlueprintPermissionFactory.create(
            role__permissions=[zaakprocess_starten.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.openbaar,
            },
        )
        with self.find_zaak_patcher:
            response = self.client.post(self.endpoint, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch("zac.core.camunda.start_process.views.get_rollen", return_value=[])
    def test_has_perm(self, m, *mocks):
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")
        m.get(
            f"{OBJECTTYPES_ROOT}objecttypes",
            json=paginated_response([START_CAMUNDA_PROCESS_FORM_OT]),
        )
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.zaaktype)
        m.post(
            f"{OBJECTS_ROOT}objects/search",
            json=paginated_response([START_CAMUNDA_PROCESS_FORM_OBJ]),
        )
        # gives them access to the page, zaaktype and VA specified -> visible
        BlueprintPermissionFactory.create(
            role__permissions=[zaakprocess_starten.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus["domein"],
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
        with self.find_zaak_patcher:
            response = self.client.post(self.endpoint, {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch("zac.core.camunda.start_process.views.get_rollen", return_value=[])
    def test_has_no_perm_to_force_restart(self, m, *mocks):
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")
        m.get(
            f"{OBJECTTYPES_ROOT}objecttypes",
            json=paginated_response([START_CAMUNDA_PROCESS_FORM_OT]),
        )
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.zaaktype)
        m.post(
            f"{OBJECTS_ROOT}objects/search",
            json=paginated_response([START_CAMUNDA_PROCESS_FORM_OBJ]),
        )
        # gives them access to the page, zaaktype and VA specified -> visible
        BlueprintPermissionFactory.create(
            role__permissions=[zaakprocess_starten.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            },
        )
        zaak_object = deepcopy(self.zaak_obj)
        zaak_object.einddatum = datetime.date(2020, 1, 1)
        with patch(
            "zac.core.camunda.start_process.views.StartCamundaProcessView.get_object",
            return_value=zaak_object,
        ):
            response = self.client.post(self.endpoint, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch("zac.core.camunda.start_process.views.get_rollen", return_value=[])
    def test_has_perm_to_force_restart(self, m, *mocks):
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")
        m.get(
            f"{OBJECTTYPES_ROOT}objecttypes",
            json=paginated_response([START_CAMUNDA_PROCESS_FORM_OT]),
        )
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.zaaktype)
        m.post(
            f"{OBJECTS_ROOT}objects/search",
            json=paginated_response([START_CAMUNDA_PROCESS_FORM_OBJ]),
        )
        # gives them access to the page, zaaktype and VA specified -> visible
        BlueprintPermissionFactory.create(
            role__permissions=[
                zaakprocess_starten.name,
                zaken_geforceerd_bijwerken.name,
            ],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus["domein"],
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
            f"{CAMUNDA_URL}process-definition/key/{START_CAMUNDA_PROCESS_FORM['camundaProcessDefinitionKey']}/start",
            status_code=201,
            json={
                "links": [{"rel": "self", "href": "https://some-url.com/"}],
                "id": PROCESS_INSTANCE["id"],
            },
        )

        zaak_object = deepcopy(self.zaak_obj)
        zaak_object.einddatum = datetime.date(2020, 1, 1)
        with self.find_zaak_patcher:
            response = self.client.post(self.endpoint, {})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_without_application_token(self, m):
        self.client.logout()
        response = self.client.post(self.endpoint, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("zac.core.camunda.start_process.views.get_rollen", return_value=[])
    def test_with_application_token(self, m, *mocks):
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")
        m.get(
            f"{OBJECTTYPES_ROOT}objecttypes",
            json=paginated_response([START_CAMUNDA_PROCESS_FORM_OT]),
        )
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.zaaktype)
        m.post(
            f"{OBJECTS_ROOT}objects/search",
            json=paginated_response([START_CAMUNDA_PROCESS_FORM_OBJ]),
        )
        # gives them access to the page, zaaktype and VA specified -> visible
        BlueprintPermissionFactory.create(
            role__permissions=[zaakprocess_starten.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus["domein"],
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
        token = ApplicationTokenFactory.create()
        self.client.logout()
        with self.find_zaak_patcher:
            response = self.client.post(
                self.endpoint, {}, HTTP_AUTHORIZATION=f"ApplicationToken {token.token}"
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
