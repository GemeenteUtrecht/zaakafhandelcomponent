import uuid
from pathlib import Path
from unittest.mock import patch

from django.urls import reverse

import requests_mock
from django_camunda.utils import serialize_variable, underscoreize
from freezegun import freeze_time
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import InformatieObjectType, ZaakType
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import BlueprintPermissionFactory, UserFactory
from zac.api.context import ZaakContext
from zac.camunda.data import Task
from zac.contrib.kownsl.constants import KownslTypes
from zac.contrib.kownsl.data import ReviewRequest
from zac.core.models import CoreConfig
from zac.core.permissions import zaakproces_usertasks
from zac.core.tests.utils import ClearCachesMixin
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
    "formKey": None,
    "tenantId": "aTenantId",
}


def _get_task(**overrides):
    data = underscoreize({**TASK_DATA, **overrides})
    return factory(Task, data)


@requests_mock.Mocker()
class GetUserTaskContextViewTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory.create()

        Service.objects.create(
            label="Catalogi API",
            api_type=APITypes.ztc,
            api_root=CATALOGI_ROOT,
        )

        cls.catalogus = (
            f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        )
        Service.objects.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)
        document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
        )
        cls.document = factory(Document, document)

        cls.documenttype = generate_oas_component(
            "ztc",
            "schemas/InformatieObjectType",
            url=f"{CATALOGI_ROOT}informatieobjecttypen/d5d7285d-ce95-4f9e-a36f-181f1c642aa6",
            omschrijving="bijlage",
            catalogus=cls.catalogus,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
        )
        cls.document.informatieobjecttype = factory(
            InformatieObjectType, cls.documenttype
        )

        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            catalogus=cls.catalogus,
            url=f"{CATALOGI_ROOT}zaaktypen/d66790b7-8b01-4005-a4ba-8fcf2a60f21d",
            identificatie="ZT1",
            omschrijving="ZT1",
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

        cls.zaak_context = ZaakContext(
            zaak=cls.zaak,
            zaaktype=cls.zaaktype_obj,
            documents=[
                cls.document,
            ],
        )
        cls.patch_get_process_zaak_url = patch(
            "zac.core.camunda.select_documents.context.get_process_zaak_url",
            return_value=cls.zaak.url,
        )

        cls.patch_get_zaaktype = patch(
            "zac.core.camunda.select_documents.context.get_zaaktype_from_identificatie",
            return_value=cls.zaaktype_obj,
        )

        cls.patch_get_informatieobjecttypen_for_zaaktype = patch(
            "zac.core.camunda.select_documents.context.get_informatieobjecttypen_for_zaaktype",
            return_value=[factory(InformatieObjectType, cls.documenttype)],
        )

        cls.task_endpoint = reverse(
            "user-task-data", kwargs={"task_id": TASK_DATA["id"]}
        )

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.user)

        self.patch_get_process_zaak_url.start()
        self.addCleanup(self.patch_get_process_zaak_url.stop)

        self.patch_get_zaaktype.start()
        self.addCleanup(self.patch_get_zaaktype.stop)

        self.patch_get_informatieobjecttypen_for_zaaktype.start()
        self.addCleanup(self.patch_get_informatieobjecttypen_for_zaaktype.stop)

    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(**{"formKey": "zac:documentSelectie"}),
    )
    def test_get_context_no_permission(self, m, gt):
        user = UserFactory.create()
        self.client.force_authenticate(user)
        response = self.client.get(self.task_endpoint)
        self.assertEqual(response.status_code, 403)

    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(**{"formKey": "zac:documentSelectie"}),
    )
    def test_get_select_document_context(self, m, gt):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        BlueprintPermissionFactory.create(
            role__permissions=[zaakproces_usertasks.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        with patch(
            "zac.core.camunda.select_documents.context.get_zaak",
            return_value=self.zaak,
        ):
            with patch(
                "zac.core.camunda.select_documents.context.get_documenten",
                return_value=[[], []],
            ):
                with patch(
                    "zac.core.camunda.select_documents.context.resolve_documenten_informatieobjecttypen",
                    return_value=[self.document],
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
                    "documentType",
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
    def test_get_configure_advice_review_request_context(self, m, gt):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        BlueprintPermissionFactory.create(
            role__permissions=[zaakproces_usertasks.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        with patch(
            "zac.contrib.kownsl.camunda.get_zaak_context",
            return_value=self.zaak_context,
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
    def test_get_configure_approval_review_request_context(self, m, gt):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        BlueprintPermissionFactory.create(
            role__permissions=[zaakproces_usertasks.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        with patch(
            "zac.contrib.kownsl.camunda.get_zaak_context",
            return_value=self.zaak_context,
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
    def test_get_validsign_context(self, m, gt):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        BlueprintPermissionFactory.create(
            role__permissions=[zaakproces_usertasks.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        with patch(
            "zac.contrib.validsign.camunda.get_zaak_context",
            return_value=self.zaak_context,
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
                    "documentType",
                    "url",
                    "beschrijving",
                    "versie",
                ]
            ),
        )

    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(**{"formKey": "zac:startProcessForm"}),
    )
    @patch(
        "zac.core.camunda.start_process.serializers.get_object_or_404",
        return_value=None,
    )
    @patch(
        "zac.core.camunda.start_process.serializers.get_required_process_informatie_objecten",
        return_value=[],
    )
    @patch(
        "zac.core.camunda.start_process.serializers.get_required_rollen",
        return_value=[],
    )
    @patch(
        "zac.core.camunda.start_process.serializers.get_required_zaakeigenschappen",
        return_value=[],
    )
    def test_get_start_camunda_process_form_context(self, m, *mocks):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        BlueprintPermissionFactory.create(
            role__permissions=[zaakproces_usertasks.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        with patch(
            "zac.core.camunda.start_process.serializers.get_zaak_context",
            return_value=self.zaak_context,
        ):
            response = self.client.get(self.task_endpoint)

        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(sorted(list(data.keys())), sorted(["form", "task", "context"]))
        self.assertIn("bijlagen", data["context"].keys())
        self.assertIn("rollen", data["context"].keys())
        self.assertIn("zaakeigenschappen", data["context"].keys())


@requests_mock.Mocker()
class PutUserTaskViewTests(ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory.create()

        drc = Service.objects.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)
        config = CoreConfig.get_solo()
        config.primary_drc = drc
        config.save()
        cls.document_dict = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
        )

        cls.document = factory(Document, cls.document_dict)
        Service.objects.create(
            label="Catalogi API",
            api_type=APITypes.ztc,
            api_root=CATALOGI_ROOT,
        )
        cls.catalogus = (
            f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        )
        cls.documenttype = generate_oas_component(
            "ztc",
            "schemas/InformatieObjectType",
            url=f"{CATALOGI_ROOT}informatieobjecttypen/d5d7285d-ce95-4f9e-a36f-181f1c642aa6",
            omschrijving="bijlage",
            catalogus=cls.catalogus,
        )

        cls.document.informatieobjecttype = factory(
            InformatieObjectType, cls.documenttype
        )

        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            catalogus=cls.catalogus,
            url=f"{CATALOGI_ROOT}zaaktypen/d66790b7-8b01-4005-a4ba-8fcf2a60f21d",
            identificatie="ZT1",
            informatieobjecttypen=[
                cls.document.informatieobjecttype.url,
            ],
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
        cls.zaak_context = ZaakContext(
            zaak=cls.zaak,
            zaaktype=cls.zaaktype_obj,
            documents=[
                cls.document,
            ],
        )
        cls.patch_get_documenten_validator = patch(
            "zac.core.api.validators.get_documenten",
            return_value=([cls.document], []),
        )
        cls.patch_resolve_document_informatieobjecttypen = patch(
            "zac.core.api.validators.get_documenten",
            return_value=([cls.document], []),
        )

        cls.patch_fetch_zaaktype = patch(
            "zac.core.camunda.select_documents.serializers.get_zaaktype_from_identificatie",
            return_value=cls.zaaktype_obj,
        )
        cls.task_endpoint = reverse(
            "user-task-data", kwargs={"task_id": TASK_DATA["id"]}
        )

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.user)

        self.patch_get_documenten_validator.start()
        self.addCleanup(self.patch_get_documenten_validator.stop)

        self.patch_fetch_zaaktype.start()
        self.addCleanup(self.patch_fetch_zaaktype.stop)

    def _mock_permissions(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        BlueprintPermissionFactory.create(
            role__permissions=[zaakproces_usertasks.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(**{"formKey": "zac:documentSelectie"}),
    )
    def test_put_user_task_no_permission(self, m, gt):
        user = UserFactory.create()
        self.client.force_authenticate(user)
        response = self.client.put(self.task_endpoint)
        self.assertEqual(response.status_code, 403)

    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(**{"formKey": "zac:documentSelectie"}),
    )
    @patch("zac.camunda.api.views.complete_task", return_value=None)
    @patch(
        "zac.core.camunda.select_documents.serializers.validate_zaak_documents",
        return_value=None,
    )
    def test_put_select_document_user_task(self, m, *mocks):
        mock_service_oas_get(m, DOCUMENTS_ROOT, "drc")

        self._mock_permissions(m)
        payload = {
            "selectedDocuments": [
                {
                    "document": self.document.url,
                    "document_type": self.document.informatieobjecttype.url,
                },
            ],
        }

        m.get(
            f"https://camunda.example.com/engine-rest/process-instance/c6a5e447-c58e-4986-a30d-54fce7503bbf/variables/zaaktype?deserializeValues=false",
            json=serialize_variable(self.zaaktype["url"]),
        )
        m.get(
            f"https://camunda.example.com/engine-rest/process-instance/c6a5e447-c58e-4986-a30d-54fce7503bbf/variables/bronorganisatie?deserializeValues=false",
            json=serialize_variable("123456789"),
        )
        m.post(
            f"https://camunda.example.com/engine-rest/task/{TASK_DATA['id']}/assignee",
            status_code=201,
        )

        with patch(
            "zac.core.camunda.select_documents.serializers.get_document",
            return_value=self.document,
        ):
            with patch(
                "zac.core.camunda.select_documents.serializers.download_document",
                return_value=(self.document, b"some-content"),
            ):
                with patch(
                    "zac.core.camunda.select_documents.serializers.create_document",
                    return_value=self.document,
                ):
                    with patch(
                        "zac.core.camunda.select_documents.serializers.get_zaak_context",
                        return_value=self.zaak_context,
                    ):

                        response = self.client.put(self.task_endpoint, payload)

        self.assertEqual(response.status_code, 204)

    @freeze_time("1999-12-31T23:59:59Z")
    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(**{"formKey": "zac:configureApprovalRequest"}),
    )
    @patch("zac.camunda.api.views.complete_task", return_value=None)
    def test_put_configure_advice_review_request_user_task(self, m, gt, ct):
        self._mock_permissions(m)
        users = UserFactory.create_batch(3)
        payload = {
            "assignedUsers": [
                {
                    "user_assignees": [user.username for user in users],
                    "group_assignees": [],
                    "email_notification": False,
                    "deadline": "2020-01-01",
                },
            ],
            "selectedDocuments": [self.document.url],
            "toelichting": "some-toelichting",
        }
        review_request_data = {
            "id": uuid.uuid4(),
            "created": "2020-01-01T15:15:22Z",
            "forZaak": self.zaak.url,
            "reviewType": KownslTypes.approval,
            "documents": [self.document],
            "frontendUrl": "http://some.kownsl.com/frontendurl/",
            "numAdvices": 0,
            "numApprovals": 1,
            "numAssignedUsers": 1,
            "toelichting": "some-toelichting",
            "userDeadlines": {},
            "requester": {
                "username": "some-henkie",
                "firstName": "",
                "lastName": "",
                "fullName": "",
            },
        }
        review_request = factory(ReviewRequest, review_request_data)

        m.post(
            f"https://camunda.example.com/engine-rest/task/{TASK_DATA['id']}/assignee",
            status_code=201,
        )
        with patch(
            "zac.core.camunda.select_documents.serializers.get_zaak_context",
            return_value=self.zaak_context,
        ):
            with patch(
                "zac.contrib.kownsl.camunda.get_zaak_context",
                return_value=self.zaak_context,
            ):
                with patch(
                    "zac.contrib.kownsl.camunda.create_review_request",
                    return_value=review_request,
                ):
                    response = self.client.put(self.task_endpoint, payload)
        self.assertEqual(response.status_code, 204)

    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(**{"formKey": "zac:validSign:configurePackage"}),
    )
    @patch("zac.camunda.api.views.complete_task", return_value=None)
    def test_put_validsign_user_task(self, m, gt, ct):
        self._mock_permissions(m)

        user = UserFactory.create(
            first_name="first_name",
            last_name="last_name",
            email="some@email.com",
        )
        payload = {
            "assignedUsers": [{"username": user.username}],
            "selectedDocuments": [self.document.url],
        }
        m.post(
            f"https://camunda.example.com/engine-rest/task/{TASK_DATA['id']}/assignee",
            status_code=201,
        )
        with patch(
            "zac.core.camunda.select_documents.serializers.get_zaak_context",
            return_value=self.zaak_context,
        ):
            with patch(
                "zac.contrib.validsign.camunda.get_zaak_context",
                return_value=self.zaak_context,
            ):
                response = self.client.put(self.task_endpoint, payload)

        self.assertEqual(response.status_code, 204)

    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(**{"formKey": "keuze"}),
    )
    @patch("zac.camunda.api.views.complete_task", return_value=None)
    def test_put_named_camunda_form_user_task(
        self, m, mock_get_task, mock_complete_task
    ):
        FILES_DIR = Path(__file__).parent / "files"

        with open(FILES_DIR / "keuze-form.bpmn", "r") as bpmn:
            response = {
                "id": "aProcDefId",
                "bpmn20Xml": bpmn.read(),
            }
        m.get(
            f"https://camunda.example.com/engine-rest/process-definition/aProcDefId/xml",
            headers={"Content-Type": "application/json"},
            json=response,
        )
        m.post(
            f"https://camunda.example.com/engine-rest/task/{TASK_DATA['id']}/assignee",
            status_code=201,
        )
        self._mock_permissions(m)
        payload = {
            "resultaat": "Vastgesteld",
        }
        response = self.client.put(self.task_endpoint, payload)
        self.assertEqual(response.status_code, 204)

    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(),
    )
    @patch("zac.camunda.api.views.complete_task", return_value=None)
    def test_put_empty_formkey_user_task(self, m, mock_get_task, mock_complete_task):
        FILES_DIR = Path(__file__).parent / "files"

        with open(FILES_DIR / "keuze-form.bpmn", "r") as bpmn:
            response = {
                "id": "aProcDefId",
                "bpmn20Xml": bpmn.read(),
            }
        m.get(
            f"https://camunda.example.com/engine-rest/process-definition/aProcDefId/xml",
            headers={"Content-Type": "application/json"},
            json=response,
        )
        m.post(
            f"https://camunda.example.com/engine-rest/task/{TASK_DATA['id']}/assignee",
            status_code=201,
        )

        self._mock_permissions(m)
        payload = {
            "resultaat": "Vastgesteld",
        }
        response = self.client.put(self.task_endpoint, payload)
        self.assertEqual(response.status_code, 204)

    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(**{"formKey": "zac:startProcessForm"}),
    )
    @patch("zac.camunda.api.views.complete_task", return_value=None)
    @patch(
        "zac.core.camunda.start_process.serializers.ConfigureZaakProcessSerializer.validate_bijlagen",
        return_value=["some-bijlage"],
    )
    @patch(
        "zac.core.camunda.start_process.serializers.ConfigureZaakProcessSerializer.validate_rollen",
        return_value=[],
    )
    @patch(
        "zac.core.camunda.start_process.serializers.ConfigureZaakProcessSerializer.validate_zaakeigenschappen",
        return_value=[],
    )
    def test_put_configure_zaak_process_user_task(self, m, *mocks):
        self._mock_permissions(m)
        payload = {}

        m.post(
            f"https://camunda.example.com/engine-rest/task/{TASK_DATA['id']}/assignee",
            status_code=201,
        )
        with patch(
            "zac.core.camunda.start_process.serializers.get_zaak_context",
            return_value=self.zaak_context,
        ):
            response = self.client.put(self.task_endpoint, payload)
        self.assertEqual(response.status_code, 204)
