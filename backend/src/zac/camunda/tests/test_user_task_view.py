import uuid
from unittest.mock import MagicMock, patch

from django.urls import reverse

import requests_mock
from django_camunda.utils import underscoreize
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import PermissionSetFactory, UserFactory
from zac.camunda.data import Task
from zac.contrib.kownsl.constants import KownslTypes
from zac.core.permissions import zaakproces_usertasks
from zac.tests.utils import paginated_response
from zgw.models.zrc import Zaak

DOCUMENTS_ROOT = "http://documents.nl/api/v1/"
ZAKEN_ROOT = "http://zaken.nl/api/v1/"
CATALOGI_ROOT = "https://open-zaak.nl/catalogi/api/v1/"

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


lijstje = [
    "zac:gebruikerSelectie",
    "zac:documentSelectie",
    "",
    "zac:doRedirect",
    "zac:configureAdviceRequest",
    "zac:configureApprovalRequest",
    "zac:validSign:configurePackage",
]


@requests_mock.Mocker()
class GetContextSerializersTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory.create()

        Service.objects.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)
        document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
        )
        cls.document = factory(Document, document)

        Service.objects.create(
            label="Catalogi API",
            api_type=APITypes.ztc,
            api_root=CATALOGI_ROOT,
        )

        cls.catalogus = (
            f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            catalogus=cls.catalogus,
            url=f"{CATALOGI_ROOT}zaaktypen/d66790b7-8b01-4005-a4ba-8fcf2a60f21d",
            identificatie="ZT1",
        )

        cls.zaaktype_obj = factory(ZaakType, cls.zaaktype)

        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7",
            zaaktype=cls.zaaktype["url"],
        )

        cls.zaak = factory(Zaak, zaak)

        cls.task_endpoint = reverse(
            "user-task-data", kwargs={"task_id": TASK_DATA["id"]}
        )

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.user)

    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(**{"formKey": "zac:documentSelectie"}),
    )
    @patch(
        "zac.camunda.select_documents.context.get_process_instance", return_value=None
    )
    @patch(
        "zac.camunda.select_documents.context.get_process_zaak_url", return_value=None
    )
    def test_get_context_zac_document_selectie_no_permission(self, m, gt, gpi, gpzu):
        user = UserFactory.create()
        self.client.force_authenticate(user)
        with patch(
            "zac.camunda.select_documents.context.get_zaak", return_value=self.zaak
        ):
            with patch(
                "zac.camunda.select_documents.context.get_documenten",
                return_value=[[self.document], None],
            ):
                response = self.client.get(self.task_endpoint)
        self.assertEqual(response.status_code, 403)

    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(**{"formKey": "zac:documentSelectie"}),
    )
    @patch(
        "zac.camunda.select_documents.context.get_process_instance", return_value=None
    )
    @patch(
        "zac.camunda.select_documents.context.get_process_zaak_url", return_value=None
    )
    def test_get_context_zac_document_selectie(self, m, gt, gpi, gpzu):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        PermissionSetFactory.create(
            permissions=[zaakproces_usertasks.name],
            for_user=self.user,
            catalogus=self.catalogus,
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.zeer_geheim,
        )
        with patch(
            "zac.camunda.select_documents.context.get_zaak", return_value=self.zaak
        ):
            with patch(
                "zac.camunda.select_documents.context.get_documenten",
                return_value=[[self.document], None],
            ):

                response = self.client.get(self.task_endpoint)

        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(sorted(list(data.keys())), sorted(["form", "task", "context"]))
        self.assertIn("documents", data["context"].keys())

        self.assertEqual(
            sorted(list(data["context"]["documents"][0].keys())),
            sorted(
                [
                    "beschrijving",
                    "bestandsnaam",
                    "bestandsomvang",
                    "url",
                    "readUrl",
                    "versie",
                ]
            ),
        )

    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(**{"formKey": "zac:configureAdviceRequest"}),
    )
    @patch("zac.contrib.kownsl.camunda.get_process_instance", return_value=None)
    @patch("zac.contrib.kownsl.camunda.get_process_zaak_url", return_value=None)
    def test_get_context_advice_review_request(self, m, gt, gpi, gpzu):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        PermissionSetFactory.create(
            permissions=[zaakproces_usertasks.name],
            for_user=self.user,
            catalogus=self.catalogus,
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.zeer_geheim,
        )
        with patch("zac.contrib.kownsl.camunda.get_zaak", return_value=self.zaak):
            with patch(
                "zac.contrib.kownsl.camunda.get_documenten",
                return_value=[[self.document], None],
            ):
                with patch(
                    "zac.contrib.kownsl.camunda.fetch_zaaktype",
                    return_value=self.zaaktype_obj,
                ):
                    response = self.client.get(self.task_endpoint)

        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(sorted(list(data.keys())), sorted(["form", "task", "context"]))

        self.assertEqual(
            sorted(list(data["context"].keys())),
            sorted(["zaakInformatie", "title", "documents", "reviewType"]),
        )

        self.assertEqual(data["context"]["reviewType"], KownslTypes.advice)
        self.assertEqual(
            sorted(list(data["context"]["zaakInformatie"].keys())),
            sorted(["omschrijving", "toelichting"]),
        )

    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(**{"formKey": "zac:configureApprovalRequest"}),
    )
    @patch("zac.contrib.kownsl.camunda.get_process_instance", return_value=None)
    @patch("zac.contrib.kownsl.camunda.get_process_zaak_url", return_value=None)
    def test_get_context_approval_review_request(self, m, gt, gpi, gpzu):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        PermissionSetFactory.create(
            permissions=[zaakproces_usertasks.name],
            for_user=self.user,
            catalogus=self.catalogus,
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.zeer_geheim,
        )
        with patch("zac.contrib.kownsl.camunda.get_zaak", return_value=self.zaak):
            with patch(
                "zac.contrib.kownsl.camunda.get_documenten",
                return_value=[[self.document], None],
            ):
                with patch(
                    "zac.contrib.kownsl.camunda.fetch_zaaktype",
                    return_value=self.zaaktype_obj,
                ):
                    response = self.client.get(self.task_endpoint)

        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(sorted(list(data.keys())), sorted(["form", "task", "context"]))

        self.assertEqual(
            sorted(list(data["context"].keys())),
            sorted(["zaakInformatie", "title", "documents", "reviewType"]),
        )

        self.assertEqual(data["context"]["reviewType"], KownslTypes.approval)
        self.assertEqual(
            sorted(list(data["context"]["zaakInformatie"].keys())),
            sorted(["omschrijving", "toelichting"]),
        )
        self.assertEqual(
            sorted(list(data["context"]["documents"][0].keys())),
            sorted(["beschrijving", "bestandsnaam", "readUrl", "url"]),
        )

    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(**{"formKey": "zac:validSign:configurePackage"}),
    )
    @patch("zac.contrib.validsign.camunda.get_process_instance", return_value=None)
    @patch("zac.contrib.validsign.camunda.get_process_zaak_url", return_value=None)
    def test_get_context_approval_review_request(self, m, gt, gpi, gpzu):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        PermissionSetFactory.create(
            permissions=[zaakproces_usertasks.name],
            for_user=self.user,
            catalogus=self.catalogus,
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.zeer_geheim,
        )
        with patch("zac.contrib.validsign.camunda.get_zaak", return_value=self.zaak):
            with patch(
                "zac.contrib.validsign.camunda.get_documenten",
                return_value=[[self.document], None],
            ):
                response = self.client.get(self.task_endpoint)

        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(sorted(list(data.keys())), sorted(["form", "task", "context"]))
        self.assertIn("documents", data["context"].keys())

        self.assertEqual(
            sorted(list(data["context"]["documents"][0].keys())),
            sorted(
                [
                    "readUrl",
                    "bestandsnaam",
                    "bestandsomvang",
                    "url",
                    "beschrijving",
                    "versie",
                ]
            ),
        )
