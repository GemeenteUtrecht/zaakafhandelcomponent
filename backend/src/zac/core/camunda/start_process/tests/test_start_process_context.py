from unittest.mock import patch

from django.urls import reverse

import requests_mock
from django_camunda.utils import serialize_variable, underscoreize
from rest_framework import exceptions
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import InformatieObjectType, ZaakType
from zgw_consumers.api_models.constants import (
    RolOmschrijving,
    RolTypes,
    VertrouwelijkheidsAanduidingen,
)
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import SuperUserFactory, UserFactory
from zac.api.context import ZaakContext
from zac.camunda.data import Task
from zac.camunda.user_tasks import UserTaskData, get_context as _get_context
from zac.contrib.dowc.constants import DocFileTypes
from zac.contrib.dowc.utils import get_dowc_url
from zac.core.camunda.start_process.serializers import (
    CamundaZaakProcessContextSerializer,
)
from zac.core.models import CoreConfig
from zac.tests.utils import mock_resource_get, paginated_response
from zgw.models.zrc import Zaak

from ..serializers import StartProcessFormContext
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
class GetCamundaZaakProcessContextUserTaskViewTests(APITestCase):
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
            zaaktype=cls.zaaktype["url"],
            naam="some-property",
            specificatie={
                "groep": "dummy",
                "formaat": "tekst",
                "lengte": "3",
                "kardinaliteit": "1",
                "waardenverzameling": ["aaa", "bbb"],
            },
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
            url=f"{ZAKEN_ROOT}/zaakeigenschappen/cc20d728-145b-4309-b797-9743826b220d",
            zaak=cls.zaak["url"],
            eigenschap=cls.eigenschap["url"],
            naam=cls.eigenschap["naam"],
            waarde="aaa",
        )
        cls.informatieobjecttype = generate_oas_component(
            "ztc",
            "schemas/InformatieObjectType",
            url=f"{CATALOGI_ROOT}informatieobjecttypen/d5d7285d-ce95-4f9e-a36f-181f1c642aa6",
            omschrijving="bijlage",
            catalogus=catalogus_url,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
        )
        cls.document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            informatieobjecttype=cls.informatieobjecttype["url"],
        )
        cls.roltype = generate_oas_component(
            "ztc",
            "schemas/RolType",
            url=f"{CATALOGI_ROOT}roltypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
            zaaktype=cls.zaaktype["url"],
            omschrijvingGeneriek="klantcontacter",
            omschrijving="some-omschrijving",
        )
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
            zaak=cls.zaak["url"],
            betrokkene="",
            betrokkeneType="medewerker",
            roltype=cls.roltype["url"],
            betrokkeneIdentificatie=cls.medewerker,
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
            betrokkene_type="natuurlijk_persoon",
        )

    def setUp(self):
        self.client.force_authenticate(self.user)

    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(**{"formKey": "zac:startProcessForm"}),
    )
    def test_get_start_process_context_user_task_everything_done(self, m, gt):
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

        with patch(
            "zac.core.camunda.start_process.serializers.get_zaak_context",
            return_value=self.zaak_context,
        ):
            with patch(
                "zac.core.camunda.start_process.utils.get_informatieobjecttypen_for_zaaktype",
                return_value=[factory(InformatieObjectType, self.informatieobjecttype)],
            ):
                response = self.client.get(self.task_endpoint)

        self.assertEqual(
            response.json(),
            {
                "form": "zac:startProcessForm",
                "task": {
                    "id": "598347ee-62fc-46a2-913a-6e0788bc1b8c",
                    "name": "aName",
                    "created": "2013-01-23T11:42:42Z",
                    "hasForm": False,
                    "assigneeType": "",
                    "canCancelTask": False,
                    "assignee": None,
                },
                "context": {
                    "benodigdeBijlagen": [
                        {
                            "informatieobjecttype": {
                                "url": self.informatieobjecttype["url"],
                                "omschrijving": self.informatieobjecttype[
                                    "omschrijving"
                                ],
                            },
                            "alreadyUploadedInformatieobjecten": [self.document["url"]],
                            "allowMultiple": True,
                            "label": "some-doc",
                        }
                    ],
                    "benodigdeRollen": [],
                    "benodigdeZaakeigenschappen": [],
                },
            },
        )

    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(**{"formKey": "zac:startProcessForm"}),
    )
    def test_get_start_process_context_user_task_missing_everything(self, m, gt):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")

        m.get(
            f"{CATALOGI_ROOT}informatieobjecttypen",
            json=paginated_response([self.informatieobjecttype]),
        )
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}",
            json=paginated_response([]),
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
            json=[],
        )

        zaak_context = ZaakContext(
            zaak=self.zaak_context.zaak,
            zaaktype=self.zaak_context.zaaktype,
            documents=[],
        )
        with patch(
            "zac.core.camunda.start_process.serializers.get_zaak_context",
            return_value=zaak_context,
        ):
            with patch(
                "zac.core.camunda.start_process.utils.get_informatieobjecttypen_for_zaaktype",
                return_value=[factory(InformatieObjectType, self.informatieobjecttype)],
            ):
                response = self.client.get(self.task_endpoint)

        self.maxDiff = None
        self.assertEqual(
            response.json(),
            {
                "form": "zac:startProcessForm",
                "task": {
                    "id": "598347ee-62fc-46a2-913a-6e0788bc1b8c",
                    "name": "aName",
                    "created": "2013-01-23T11:42:42Z",
                    "hasForm": False,
                    "assigneeType": "",
                    "canCancelTask": False,
                    "assignee": None,
                },
                "context": {
                    "benodigdeBijlagen": [
                        {
                            "informatieobjecttype": {
                                "url": "http://catalogus.nl/api/v1/informatieobjecttypen/d5d7285d-ce95-4f9e-a36f-181f1c642aa6",
                                "omschrijving": "bijlage",
                            },
                            "allowMultiple": True,
                            "label": "some-doc",
                        }
                    ],
                    "benodigdeRollen": [
                        {
                            "roltype": {
                                "url": "http://catalogus.nl/api/v1/roltypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
                                "omschrijving": "some-omschrijving",
                                "omschrijvingGeneriek": "klantcontacter",
                            },
                            "label": "some-rol",
                            "betrokkeneType": "natuurlijk_persoon",
                            "default": "",
                        }
                    ],
                    "benodigdeZaakeigenschappen": [
                        {
                            "choices": [
                                {
                                    "label": "some-choice-1",
                                    "value": "some-value-1",
                                }
                            ],
                            "eigenschap": {
                                "url": self.eigenschap["url"],
                                "naam": "some-property",
                                "toelichting": self.eigenschap["toelichting"],
                                "specificatie": {
                                    "groep": "dummy",
                                    "formaat": "tekst",
                                    "lengte": "3",
                                    "kardinaliteit": "1",
                                    "waardenverzameling": ["aaa", "bbb"],
                                },
                            },
                            "label": "some-eigenschap",
                            "default": "",
                        }
                    ],
                },
            },
        )
