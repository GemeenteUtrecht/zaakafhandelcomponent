from unittest.mock import patch

from django.urls import reverse_lazy

import requests_mock
from django_camunda.client import get_client
from django_camunda.models import CamundaConfig
from django_camunda.utils import underscoreize
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes

from zac.accounts.tests.factories import (
    BlueprintPermissionFactory,
    SuperUserFactory,
    UserFactory,
)
from zac.camunda.data import ProcessInstance, Task
from zac.core.tests.utils import ClearCachesMixin, mock_parallel
from zac.tests import ServiceFactory
from zac.tests.compat import generate_oas_component, mock_service_oas_get
from zac.tests.utils import mock_resource_get, paginated_response

from ..api.permissions import zaakproces_usertasks

ZAKEN_ROOT = "https://some.zrc.nl/api/v1/"
CATALOGI_ROOT = "https://some.ztc.nl/api/v1/"
ZAAK = f"{ZAKEN_ROOT}zaken/f3ff2713-2f53-42ff-a154-16842309ad60"
ZAAKTYPE = f"{CATALOGI_ROOT}zaaktypen/ad4573d0-4d99-4e90-a05c-e08911e8673d"
CATALOGUS = f"{CATALOGI_ROOT}catalogussen/2bd772a5-f1a4-458b-8c13-d2f85c2bfa89"
STATUS = f"{ZAKEN_ROOT}statussen/dd4573d0-4d99-4e90-a05c-e08911e8673e"
IDENTIFICATIE = "ZAAK-123"
ROL = f"{ZAKEN_ROOT}rollen/69e98129-1f0d-497f-bbfb-84b88137edbc"
ROLTYPE = f"{CATALOGI_ROOT}roltypen/bfd62804-f46c-42e7-a31c-4139b4c661ac"

# Taken from https://docs.camunda.org/manual/7.13/reference/rest/task/get/
TASK_DATA = {
    "id": "598347ee-62fc-46a2-913a-6e0788bc1b8c",
    "name": "aName",
    "assignee": None,
    "created": "2013-01-23T13:42:42.000+0200",
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
    "formKey": None,
    "tenantId": "aTenantId",
}


def _get_task(**overrides):
    data = underscoreize({**TASK_DATA, **overrides})
    return factory(Task, data)


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
class UpdateCamundaBehandelaarViewTests(ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        ServiceFactory.create(api_root=ZAKEN_ROOT, api_type=APITypes.zrc)
        ServiceFactory.create(api_root=CATALOGI_ROOT, api_type=APITypes.ztc)
        cls.catalogus = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=CATALOGUS,
            domein="DOME",
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=ZAAKTYPE,
            catalogus=cls.catalogus["url"],
        )
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=ZAAK,
            zaaktype=ZAAKTYPE,
        )

        cls.roltype = generate_oas_component(
            "ztc",
            "schemas/RolType",
            url=ROLTYPE,
            zaaktype=ZAAKTYPE,
            omschrijving="zaak behandelaar",
            omschrijvingGeneriek="behandelaar",
        )
        cls.user = SuperUserFactory.create()
        cls.rol = generate_oas_component(
            "zrc",
            "schemas/Rol",
            url=ROL,
            zaak=ZAAK,
            betrokkene="",
            betrokkeneType="medewerker",
            roltype=ROLTYPE,
            omschrijving=cls.roltype["omschrijving"],
            omschrijvingGeneriek=cls.roltype["omschrijvingGeneriek"],
            roltoelichting=cls.roltype["omschrijving"],
            registratiedatum="2020-09-01T00:00:00Z",
            indicatieMachtiging="",
            betrokkeneIdentificatie={
                "identificatie": f"{cls.user}",
                "voorletters": "M.Y.",
                "achternaam": "Surname",
                "voorvoegsel_achternaam": "",
            },
        )

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)
        patchers = [
            patch(
                "zac.camunda.process_instances.get_client",
                return_value=_get_camunda_client(),
            ),
            patch(
                "zac.camunda.user_tasks.api.get_client",
                return_value=_get_camunda_client(),
            ),
            patch(
                "zac.camunda.process_instances.parallel", return_value=mock_parallel()
            ),
            patch("zac.camunda.api.serializers.parallel", return_value=mock_parallel()),
        ]
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_update_camunda_assignees(self, rm):
        mock_service_oas_get(rm, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(rm, ZAKEN_ROOT, "zrc")
        mock_resource_get(rm, self.zaak)
        mock_resource_get(rm, self.zaaktype)
        mock_resource_get(rm, self.roltype)
        user = SuperUserFactory.create(username="other-user")
        new_rol = {
            **self.rol,
            "url": f"{ZAKEN_ROOT}rollen/69e98129-1f0d-497f-bbfb-84b88137edbd",
            "betrokkeneIdentificatie": {
                "identificatie": f"{user}",
                "voorletters": "",
                "achternaam": "",
                "voorvoegsel_achternaam": "",
            },
        }
        mock_resource_get(rm, new_rol)
        rm.get(
            f"{ZAKEN_ROOT}rollen?zaak={ZAAK}",
            json=paginated_response([self.rol, new_rol]),
        )
        process_instance = factory(
            ProcessInstance,
            {
                "id": "205eae6b-d26f-11ea-86dc-e22fafe5f405",
                "definition_id": "beleid_opstellen:8:c76c8200-c766-11ea-86dc-e22fafe5f405",
            },
        )
        task = _get_task(**{"formKey": "zac:zetResultaat"})
        task.assignee = self.user
        process_instance.tasks = [task]

        rm.put(
            f"{CAMUNDA_URL}process-instance/{process_instance.id}/variables/behandelaar",
            status_code=204,
        )
        rm.put(
            f"{CAMUNDA_URL}process-instance/{process_instance.id}/variables/zaak%20behandelaar",
            status_code=204,
        )
        rm.post(
            f"{CAMUNDA_URL}task/{task.id}/assignee",
            status_code=204,
        )
        with patch(
            "zac.camunda.api.serializers.get_top_level_process_instances",
            return_value=[process_instance],
        ):
            response = self.client.post(
                reverse_lazy("change-behandelaar"),
                {"zaak": ZAAK, "rol": new_rol["url"]},
            )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(
            rm.last_request.url,
            f"{CAMUNDA_URL}task/{task.id}/assignee",
        )

    def test_update_camunda_assignees_not_updated_kownsl(self, rm):
        mock_service_oas_get(rm, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(rm, ZAKEN_ROOT, "zrc")
        mock_resource_get(rm, self.zaak)
        mock_resource_get(rm, self.zaaktype)
        mock_resource_get(rm, self.roltype)
        user = SuperUserFactory.create(username="other-user")
        new_rol = {
            **self.rol,
            "url": f"{ZAKEN_ROOT}rollen/69e98129-1f0d-497f-bbfb-84b88137edbd",
            "betrokkeneIdentificatie": {
                "identificatie": f"{user}",
                "voorletters": "",
                "achternaam": "",
                "voorvoegsel_achternaam": "",
            },
        }
        mock_resource_get(rm, new_rol)
        rm.get(
            f"{ZAKEN_ROOT}rollen?zaak={ZAAK}",
            json=paginated_response([self.rol, new_rol]),
        )
        process_instance = factory(
            ProcessInstance,
            {
                "id": "205eae6b-d26f-11ea-86dc-e22fafe5f405",
                "definition_id": "beleid_opstellen:8:c76c8200-c766-11ea-86dc-e22fafe5f405",
            },
        )
        task = _get_task(**{"name": "adviseren"})
        task.assignee = self.user
        process_instance.tasks = [task]
        rm.put(
            f"{CAMUNDA_URL}process-instance/{process_instance.id}/variables/behandelaar",
            status_code=204,
        )
        rm.put(
            f"{CAMUNDA_URL}process-instance/{process_instance.id}/variables/zaak%20behandelaar",
            status_code=204,
        )
        rm.post(
            f"{CAMUNDA_URL}task/{task.id}/assignee",
            status_code=204,
        )
        with patch(
            "zac.camunda.api.serializers.get_top_level_process_instances",
            return_value=[process_instance],
        ):
            response = self.client.post(
                reverse_lazy("change-behandelaar"),
                {"zaak": ZAAK, "rol": new_rol["url"]},
            )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(
            rm.last_request.url,
            f"{CAMUNDA_URL}process-instance/205eae6b-d26f-11ea-86dc-e22fafe5f405/variables/zaak%20behandelaar",
        )

    def test_update_camunda_assignees_zaak_does_not_exist(self, rm):
        mock_service_oas_get(rm, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(rm, ZAKEN_ROOT, "zrc")
        rm.get(f"{ZAKEN_ROOT}zaken/some-zaak", status_code=404, json={})
        rm.get(self.rol["url"], json=self.rol)
        response = self.client.post(
            reverse_lazy("change-behandelaar"),
            {"zaak": f"{ZAKEN_ROOT}zaken/some-zaak", "rol": self.rol["url"]},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_camunda_assignees_rol_does_not_exist(self, rm):
        mock_service_oas_get(rm, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(rm, ZAKEN_ROOT, "zrc")
        rm.get(f"{ZAKEN_ROOT}rollen/some-rol", status_code=404, json={})
        rm.get(self.zaak["url"], json=self.zaak)
        response = self.client.post(
            reverse_lazy("change-behandelaar"),
            {"zaak": self.zaak["url"], "rol": f"{ZAKEN_ROOT}rollen/some-rol"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


@requests_mock.Mocker()
class ChangeBehandelaarPermissionTests(ClearCachesMixin, APITestCase):
    url = reverse_lazy("change-behandelaar")

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        ServiceFactory.create(api_root=ZAKEN_ROOT, api_type=APITypes.zrc)
        ServiceFactory.create(api_root=CATALOGI_ROOT, api_type=APITypes.ztc)
        cls.catalogus = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=CATALOGUS,
            domein="DOME",
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=ZAAKTYPE,
            catalogus=CATALOGUS,
        )
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=ZAAK,
            zaaktype=ZAAKTYPE,
        )
        cls.roltype = generate_oas_component(
            "ztc",
            "schemas/RolType",
            url=ROLTYPE,
            zaaktype=ZAAKTYPE,
            omschrijving="zaak behandelaar",
            omschrijvingGeneriek="behandelaar",
        )
        cls.user = UserFactory.create()
        cls.rol = generate_oas_component(
            "zrc",
            "schemas/Rol",
            url=ROL,
            zaak=ZAAK,
            betrokkene="",
            betrokkeneType="medewerker",
            roltype=ROLTYPE,
            omschrijving=cls.roltype["omschrijving"],
            omschrijvingGeneriek=cls.roltype["omschrijvingGeneriek"],
            roltoelichting=cls.roltype["omschrijving"],
            registratiedatum="2020-09-01T00:00:00Z",
            indicatieMachtiging="",
            betrokkeneIdentificatie={
                "identificatie": f"{cls.user}",
                "voorletters": "M.Y.",
                "achternaam": "Surname",
                "voorvoegsel_achternaam": "",
            },
        )

    def test_no_user_logged_in(self, rm):
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 403)

    def test_user_logged_in_but_no_permission(self, rm):
        self.client.force_authenticate(self.user)
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 403)

    @patch(
        "zac.camunda.api.serializers.get_top_level_process_instances", return_value=[]
    )
    def test_user_logged_in_with_permission(self, rm, *mocks):
        mock_service_oas_get(rm, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(rm, ZAKEN_ROOT, "zrc")
        mock_resource_get(rm, self.catalogus)
        mock_resource_get(rm, self.zaak)
        mock_resource_get(rm, self.zaaktype)
        mock_resource_get(rm, self.rol)
        mock_resource_get(rm, self.roltype)
        BlueprintPermissionFactory.create(
            role__permissions=[zaakproces_usertasks.name],
            for_user=self.user,
            policy={
                "catalogus": "DOME",
                "zaaktype_omschrijving": self.zaaktype["omschrijving"],
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        self.client.force_authenticate(self.user)

        with patch(
            "zac.camunda.api.views.get_camunda_history_for_zaak", return_value=[]
        ):
            response = self.client.post(self.url, {"zaak": ZAAK, "rol": ROL})

        self.assertEqual(response.status_code, 204)
