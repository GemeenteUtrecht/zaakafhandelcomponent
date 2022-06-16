from unittest.mock import patch

from django.urls import reverse

import requests_mock
from django_camunda.utils import underscoreize
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import SuperUserFactory
from zac.api.context import ZaakContext
from zac.camunda.data import Task
from zac.core.tests.utils import ClearCachesMixin
from zac.tests.utils import paginated_response
from zgw.models.zrc import Zaak

from .factories import (
    CamundaStartProcessFactory,
    ProcessEigenschapChoiceFactory,
    ProcessEigenschapFactory,
    ProcessInformatieObjectFactory,
    ProcessRolFactory,
)

CATALOGI_ROOT = "http://catalogus.nl/api/v1/"
DOCUMENTS_ROOT = "http://documents.nl/api/v1/"
ZAKEN_ROOT = "http://zaken.nl/api/v1/"
PI_URL = "https://camunda.example.com/engine-rest/process-instance"

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
    "formKey": "",
    "tenantId": "aTenantId",
}


def _get_task(**overrides):
    data = underscoreize({**TASK_DATA, **overrides})
    return factory(Task, data)


@requests_mock.Mocker()
class PutCamundaZaakProcessUserTaskViewTests(ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = SuperUserFactory.create()

        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        Service.objects.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)

        catalogus_url = (
            f"{CATALOGI_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            catalogus=catalogus_url,
            url=f"{CATALOGI_ROOT}zaaktypen/4f622c65-5ffe-476e-96ee-f0710bd0c92b",
        )
        cls.eigenschap = generate_oas_component(
            "ztc",
            "schemas/Eigenschap",
            url=f"{CATALOGI_ROOT}eigenschappen/3941cb76-afc6-47d5-aa5d-6a9bfba963f6",
            zaaktype=cls.zaaktype["url"],
            naam="some-property",
            specificatie={
                "groep": "dummy",
                "formaat": "tekst",
                "lengte": "3",
                "kardinaliteit": "1",
                "waardenverzameling": ["aaa", "bbb"],
            },
            toelichting="some-toelichting",
        )
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            id="30a98ef3-bf35-4287-ac9c-fed048619dd7",
            url=f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7",
            zaaktype=cls.zaaktype["url"],
        )
        cls.zaakeigenschap = generate_oas_component(
            "zrc",
            "schemas/ZaakEigenschap",
            url=f"{ZAKEN_ROOT}zaakeigenschappen/cc20d728-145b-4309-b797-9743826b220d",
            zaak=cls.zaak["url"],
            eigenschap=cls.eigenschap["url"],
            naam=cls.eigenschap["naam"],
            waarde="some-value-1",
        )
        cls.zaak["eigenschappen"] = [cls.zaakeigenschap]
        cls.informatieobjecttype = generate_oas_component(
            "ztc",
            "schemas/InformatieObjectType",
            url=f"{CATALOGI_ROOT}informatieobjecttypen/d5d7285d-ce95-4f9e-a36f-181f1c642aa6",
            omschrijving="bijlage",
            catalogus=catalogus_url,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
        )
        cls.zaak["informatieobjecttypen"] = [cls.informatieobjecttype]
        cls.document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            url=f"{DOCUMENTS_ROOT}informatieobject/e82ae0d6-d442-436e-be55-cf5b827dfeec",
            informatieobjecttype=cls.informatieobjecttype["url"],
        )
        cls.zaakinformatieobject = generate_oas_component(
            "zrc",
            "schemas/ZaakInformatieObject",
            informatieobject=cls.document["url"],
            zaak=cls.zaak["url"],
        )
        cls.roltype = generate_oas_component(
            "ztc",
            "schemas/RolType",
            url=f"{CATALOGI_ROOT}roltypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
            zaaktype=cls.zaaktype["url"],
            omschrijvingGeneriek="klantcontacter",
            omschrijving="some-roltype-omschrijving",
        )
        cls.zaak["roltypen"] = [cls.roltype]
        cls.medewerker = generate_oas_component(
            "zrc",
            "schemas/RolMedewerker",
            identificatie="some-username",
            achternaam="Orange",
            voorletters="W.",
            voorvoegselAchternaam="van",
        )
        cls.rol = generate_oas_component(
            "zrc",
            "schemas/Rol",
            url=f"{ZAKEN_ROOT}rollen/5c2b8bf8-29a2-40bf-8c6c-7028aef896d4",
            zaak=cls.zaak["url"],
            betrokkene="",
            betrokkeneType="medewerker",
            roltype=cls.roltype["url"],
            betrokkeneIdentificatie=cls.medewerker,
            omschrijving="some-rol-omschrijving",
            registratiedatum="2004-06-23T01:52:50Z",
            roltoelichting=cls.roltype["omschrijving"],
            omschrijvingGeneriek=cls.roltype["omschrijvingGeneriek"],
        )

        cls.task_endpoint = reverse(
            "user-task-data", kwargs={"task_id": TASK_DATA["id"]}
        )

        zaak = factory(Zaak, cls.zaak)
        zaak.zaaktype = factory(ZaakType, cls.zaaktype)
        cls.zaak_context = ZaakContext(
            zaak=zaak,
            zaaktype=zaak.zaaktype,
            documents=[
                factory(Document, cls.document),
            ],
        )

        camunda_start_process = CamundaStartProcessFactory.create(
            zaaktype_identificatie=cls.zaaktype["identificatie"],
            zaaktype_catalogus=cls.zaaktype["catalogus"],
        )
        process_eigenschap = ProcessEigenschapFactory.create(
            camunda_start_process=camunda_start_process,
            eigenschapnaam=cls.eigenschap["naam"],
            label="some-eigenschap",
        )
        ProcessEigenschapChoiceFactory.create(
            process_eigenschap=process_eigenschap,
            label="some-choice-1",
            value="some-value-1",
        )
        ProcessInformatieObjectFactory.create(
            camunda_start_process=camunda_start_process,
            informatieobjecttype_omschrijving=cls.informatieobjecttype["omschrijving"],
            label="some-doc",
        )
        ProcessRolFactory.create(
            camunda_start_process=camunda_start_process,
            roltype_omschrijving=cls.roltype["omschrijving"],
            label="some-rol",
            betrokkene_type=cls.rol["betrokkeneType"],
        )

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.user)
        self.maxDiff = None

    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(**{"formKey": "zac:startProcessForm"}),
    )
    def test_put_start_process_user_task_everything_done(self, m, gt):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")

        m.get(
            f"{CATALOGI_ROOT}informatieobjecttypen",
            json=paginated_response([self.informatieobjecttype]),
        )
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}",
            json=paginated_response([self.rol]),
        )
        m.get(
            f"{CATALOGI_ROOT}roltypen?zaaktype={self.zaaktype['url']}",
            json=paginated_response([self.roltype]),
        )
        m.get(
            f"{CATALOGI_ROOT}eigenschappen?zaaktype={self.zaaktype['url']}",
            json=paginated_response([self.eigenschap]),
        )
        m.get(
            f"{ZAKEN_ROOT}zaken/{self.zaak['id']}/zaakeigenschappen",
            json=[self.zaakeigenschap],
        )
        m.get(
            f"{ZAKEN_ROOT}zaakinformatieobjecten?zaak={self.zaak['url']}",
            json=[self.zaakinformatieobject],
        )
        m.post(
            "https://camunda.example.com/engine-rest/task/598347ee-62fc-46a2-913a-6e0788bc1b8c/assignee",
            status_code=204,
        )
        m.post(
            "https://camunda.example.com/engine-rest/task/598347ee-62fc-46a2-913a-6e0788bc1b8c/complete",
            status_code=204,
        )

        with patch(
            "zac.core.camunda.start_process.serializers.get_zaak_context",
            return_value=self.zaak_context,
        ):
            response = self.client.put(self.task_endpoint)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(
            m.last_request.json(),
            {
                "variables": {
                    "bptlAppId": {"type": "String", "value": ""},
                    "bijlagen": {
                        "type": "Json",
                        "value": '["http://documents.nl/api/v1/informatieobject/e82ae0d6-d442-436e-be55-cf5b827dfeec"]',
                    },
                    "eigenschappen": {
                        "type": "Json",
                        "value": '[{"url": "http://zaken.nl/api/v1/zaakeigenschappen/cc20d728-145b-4309-b797-9743826b220d", "formaat": "tekst", "eigenschap": {"url": "http://catalogus.nl/api/v1/eigenschappen/3941cb76-afc6-47d5-aa5d-6a9bfba963f6", "naam": "some-property", "toelichting": "some-toelichting", "specificatie": {"groep": "dummy", "formaat": "tekst", "lengte": "3", "kardinaliteit": "1", "waardenverzameling": ["aaa", "bbb"]}}, "waarde": "some-value-1"}]',
                    },
                    "rollen": {
                        "type": "Json",
                        "value": '[{"url": "http://zaken.nl/api/v1/rollen/5c2b8bf8-29a2-40bf-8c6c-7028aef896d4", "betrokkene_type": "medewerker", "betrokkene_type_display": "Medewerker", "omschrijving": "some-rol-omschrijving", "omschrijving_generiek": "klantcontacter", "roltoelichting": "some-roltype-omschrijving", "registratiedatum": "2004-06-23T01:52:50Z", "name": "W. van Orange", "identificatie": "some-username"}]',
                    },
                    "some-property": {"type": "String", "value": "some-value-1"},
                    "bijlage1": {
                        "type": "String",
                        "value": "http://documents.nl/api/v1/informatieobject/e82ae0d6-d442-436e-be55-cf5b827dfeec",
                    },
                    "some-roltype-omschrijving": {
                        "type": "Json",
                        "value": '{"url": "http://zaken.nl/api/v1/rollen/5c2b8bf8-29a2-40bf-8c6c-7028aef896d4", "betrokkene_type": "medewerker", "betrokkene_type_display": "Medewerker", "omschrijving": "some-rol-omschrijving", "omschrijving_generiek": "klantcontacter", "roltoelichting": "some-roltype-omschrijving", "registratiedatum": "2004-06-23T01:52:50Z", "name": "W. van Orange", "identificatie": "some-username"}',
                    },
                }
            },
        )

    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(**{"formKey": "zac:startProcessForm"}),
    )
    @patch(
        "zac.core.camunda.start_process.serializers.get_rollen",
        return_value=[],
    )
    @patch(
        "zac.core.camunda.start_process.serializers.get_zaak_eigenschappen",
        return_value=[],
    )
    @patch(
        "zac.core.camunda.start_process.serializers.ConfigureZaakProcessSerializer.validate_rollen",
        return_value=[],
    )
    @patch(
        "zac.core.camunda.start_process.serializers.ConfigureZaakProcessSerializer.validate_zaakeigenschappen",
        return_value=[],
    )
    def test_put_start_process_user_task_missing_bijlage(self, m, *mocks):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")

        m.get(
            f"{CATALOGI_ROOT}informatieobjecttypen",
            json=paginated_response([self.informatieobjecttype]),
        )
        m.get(
            f"{ZAKEN_ROOT}zaakinformatieobjecten?zaak={self.zaak['url']}",
            json=[self.zaakinformatieobject],
        )

        zaakcontext = ZaakContext(
            zaak=self.zaak_context.zaak,
            zaaktype=self.zaak_context.zaaktype,
            documents=[],
        )
        with patch(
            "zac.core.camunda.start_process.serializers.get_zaak_context",
            return_value=zaakcontext,
        ):
            response = self.client.put(self.task_endpoint)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                "bijlagen": [
                    "A INFORMATIEOBJECT with INFORMATIEOBJECTTYPE description `bijlage` is required."
                ]
            },
        )

    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(**{"formKey": "zac:startProcessForm"}),
    )
    @patch(
        "zac.core.camunda.start_process.serializers.resolve_documenten_informatieobjecttypen",
        return_value=[],
    )
    @patch(
        "zac.core.camunda.start_process.serializers.get_zaak_eigenschappen",
        return_value=[],
    )
    @patch(
        "zac.core.camunda.start_process.serializers.ConfigureZaakProcessSerializer.validate_bijlagen",
        return_value=[],
    )
    @patch(
        "zac.core.camunda.start_process.serializers.ConfigureZaakProcessSerializer.validate_zaakeigenschappen",
        return_value=[],
    )
    def test_put_start_process_user_task_missing_rol(self, m, *mocks):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")

        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}",
            json=paginated_response([]),
        )
        m.get(
            f"{CATALOGI_ROOT}roltypen?zaaktype={self.zaaktype['url']}",
            json=paginated_response([self.roltype]),
        )

        with patch(
            "zac.core.camunda.start_process.serializers.get_zaak_context",
            return_value=self.zaak_context,
        ):
            response = self.client.put(self.task_endpoint)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                "rollen": [
                    "Required ROLTYPE omschrijving `some-roltype-omschrijving` not found in ROLlen related to ZAAK."
                ]
            },
        )

    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(**{"formKey": "zac:startProcessForm"}),
    )
    @patch(
        "zac.core.camunda.start_process.serializers.resolve_documenten_informatieobjecttypen",
        return_value=[],
    )
    @patch(
        "zac.core.camunda.start_process.serializers.get_zaak_eigenschappen",
        return_value=[],
    )
    @patch(
        "zac.core.camunda.start_process.serializers.ConfigureZaakProcessSerializer.validate_bijlagen",
        return_value=[],
    )
    @patch(
        "zac.core.camunda.start_process.serializers.ConfigureZaakProcessSerializer.validate_zaakeigenschappen",
        return_value=[],
    )
    def test_put_start_process_user_task_mismatch_rol_betrokkene_type(self, m, *mocks):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")

        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}",
            json=paginated_response(
                [{**self.rol, "betrokkeneType": "some-other-type"}]
            ),
        )
        m.get(
            f"{CATALOGI_ROOT}roltypen?zaaktype={self.zaaktype['url']}",
            json=paginated_response([self.roltype]),
        )

        with patch(
            "zac.core.camunda.start_process.serializers.get_zaak_context",
            return_value=self.zaak_context,
        ):
            response = self.client.put(self.task_endpoint)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                "rollen": [
                    "`betrokkene_type` of ROL with ROLTYPE omschrijving `some-roltype-omschrijving` does not match required betrokkene_type `medewerker`"
                ]
            },
        )

    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(**{"formKey": "zac:startProcessForm"}),
    )
    @patch(
        "zac.core.camunda.start_process.serializers.resolve_documenten_informatieobjecttypen",
        return_value=[],
    )
    @patch(
        "zac.core.camunda.start_process.serializers.get_rollen",
        return_value=[],
    )
    @patch(
        "zac.core.camunda.start_process.serializers.ConfigureZaakProcessSerializer.validate_bijlagen",
        return_value=[],
    )
    @patch(
        "zac.core.camunda.start_process.serializers.ConfigureZaakProcessSerializer.validate_rollen",
        return_value=[],
    )
    def test_put_start_process_user_task_missing_eigenschap(self, m, *mocks):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")

        m.get(
            f"{CATALOGI_ROOT}eigenschappen?zaaktype={self.zaaktype['url']}",
            json=paginated_response([self.eigenschap]),
        )
        m.get(
            f"{ZAKEN_ROOT}zaken/{self.zaak['id']}/zaakeigenschappen",
            json=[],
        )

        with patch(
            "zac.core.camunda.start_process.serializers.get_zaak_context",
            return_value=self.zaak_context,
        ):
            response = self.client.put(self.task_endpoint)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                "zaakeigenschappen": [
                    "A ZAAKEIGENCHAP with `naam`: `some-property` is required."
                ]
            },
        )

    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(**{"formKey": "zac:startProcessForm"}),
    )
    @patch(
        "zac.core.camunda.start_process.serializers.resolve_documenten_informatieobjecttypen",
        return_value=[],
    )
    @patch(
        "zac.core.camunda.start_process.serializers.get_rollen",
        return_value=[],
    )
    @patch(
        "zac.core.camunda.start_process.serializers.ConfigureZaakProcessSerializer.validate_bijlagen",
        return_value=[],
    )
    @patch(
        "zac.core.camunda.start_process.serializers.ConfigureZaakProcessSerializer.validate_rollen",
        return_value=[],
    )
    def test_put_start_process_user_task_wrong_eigenschap_choice(self, m, *mocks):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")

        m.get(
            f"{CATALOGI_ROOT}eigenschappen?zaaktype={self.zaaktype['url']}",
            json=paginated_response([self.eigenschap]),
        )
        m.get(
            f"{ZAKEN_ROOT}zaken/{self.zaak['id']}/zaakeigenschappen",
            json=[{**self.zaakeigenschap, "waarde": "some-waarde"}],
        )

        with patch(
            "zac.core.camunda.start_process.serializers.get_zaak_context",
            return_value=self.zaak_context,
        ):
            response = self.client.put(self.task_endpoint)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                "zaakeigenschappen": [
                    "ZAAKEIGENCHAP with `naam`: `some-property`, needs to have a `waarde` chosen from: ['some-choice-1']."
                ]
            },
        )