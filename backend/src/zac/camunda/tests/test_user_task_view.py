import uuid
from unittest.mock import MagicMock, patch

from django.urls import reverse

import requests_mock
from django_camunda.utils import underscoreize
from freezegun import freeze_time
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
from zac.contrib.kownsl.data import ReviewRequest
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
    "formKey": "",
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
    def test_get_context_no_permission(self, m, gt, gpi, gpzu):
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
    def test_get_select_document_context(self, m, gt, gpi, gpzu):
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
    def test_get_configure_advice_review_request_context(self, m, gt, gpi, gpzu):
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
    def test_get_configure_approval_review_request_context(self, m, gt, gpi, gpzu):
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
    def test_get_validsign_context(self, m, gt, gpi, gpzu):
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


@requests_mock.Mocker()
class PutUserTaskViewTests(ClearCachesMixin, APITestCase):
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

        cls.review_request_data = {
            "id": uuid.uuid4(),
            "created": "2020-01-01T15:15:22Z",
            "for_zaak": cls.zaak.url,
            "review_type": KownslTypes.advice,
            "documents": [cls.document],
            "frontend_url": "http://some.kownsl.com/frontendurl/",
            "num_advices": 0,
            "num_approvals": 1,
            "num_assigned_users": 1,
            "toelichting": "some-toelichting",
            "user_deadlines": {},
            "requester": "some-henkie",
        }

        cls.task_endpoint = reverse(
            "user-task-data", kwargs={"task_id": TASK_DATA["id"]}
        )

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.user)

    def _mock_permissions(self, m):
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

    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(**{"formKey": "zac:documentSelectie"}),
    )
    def test_put_user_task_no_permission(self, m, gt):
        user = UserFactory.create()
        self.client.force_authenticate(user)
        response = self.client.get(self.task_endpoint)
        self.assertEqual(response.status_code, 403)

    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(**{"formKey": "zac:documentSelectie"}),
    )
    @patch("zac.camunda.api.views.complete_task", return_value=None)
    @patch(
        "zac.camunda.select_documents.serializers.get_process_instance",
        return_value=None,
    )
    @patch(
        "zac.camunda.select_documents.serializers.get_process_zaak_url",
        return_value=None,
    )
    def test_put_select_document_user_task(self, m, gt, ct, gpi, gpzu):
        self._mock_permissions(m)
        payload = {
            "selected_documents": [self.document.url],
        }

        with patch(
            "zac.camunda.select_documents.serializers.get_zaak", return_value=self.zaak
        ):
            with patch(
                "zac.camunda.select_documents.serializers.get_documenten",
                return_value=[[self.document], None],
            ):
                response = self.client.put(self.task_endpoint, payload)
        self.assertEqual(response.status_code, 204)

    @freeze_time("1999-12-31T23:59:59Z")
    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(**{"formKey": "zac:configureAdviceRequest"}),
    )
    @patch("zac.camunda.api.views.complete_task", return_value=None)
    @patch(
        "zac.contrib.kownsl.camunda.get_process_instance",
        return_value=None,
    )
    @patch(
        "zac.contrib.kownsl.camunda.get_process_zaak_url",
        return_value=None,
    )
    def test_put_configure_advice_review_request_user_task(self, m, gt, ct, gpi, gpzu):
        self._mock_permissions(m)
        users = UserFactory.create_batch(3)
        payload = {
            "assigned_users": [
                {
                    "users": [user.username for user in users],
                    "deadline": "2020-01-01",
                },
            ],
            "selected_documents": [self.document.url],
            "toelichting": "some-toelichting",
        }

        review_request = factory(ReviewRequest, self.review_request_data)

        with patch("zac.contrib.kownsl.camunda.get_zaak", return_value=self.zaak):
            with patch(
                "zac.contrib.kownsl.camunda.get_documenten",
                return_value=[[self.document], None],
            ):
                with patch(
                    "zac.contrib.kownsl.camunda.create_review_request",
                    return_value=review_request,
                ):
                    response = self.client.put(self.task_endpoint, payload)
        self.assertEqual(response.status_code, 204)

    @freeze_time("1999-12-31T23:59:59Z")
    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(**{"formKey": "zac:configureApprovalRequest"}),
    )
    @patch("zac.camunda.api.views.complete_task", return_value=None)
    @patch(
        "zac.contrib.kownsl.camunda.get_process_instance",
        return_value=None,
    )
    @patch(
        "zac.contrib.kownsl.camunda.get_process_zaak_url",
        return_value=None,
    )
    def test_put_configure_advice_review_request_user_task(self, m, gt, ct, gpi, gpzu):
        self._mock_permissions(m)
        users = UserFactory.create_batch(3)
        payload = {
            "assigned_users": [
                {
                    "users": [user.username for user in users],
                    "deadline": "2020-01-01",
                },
            ],
            "selected_documents": [self.document.url],
            "toelichting": "some-toelichting",
        }
        revreq_data = {
            **self.review_request_data,
            **{"review_type": KownslTypes.approval},
        }
        review_request = factory(ReviewRequest, revreq_data)

        with patch("zac.contrib.kownsl.camunda.get_zaak", return_value=self.zaak):
            with patch(
                "zac.contrib.kownsl.camunda.get_documenten",
                return_value=[[self.document], None],
            ):
                with patch(
                    "zac.contrib.kownsl.camunda.create_review_request",
                    return_value=review_request,
                ):
                    response = self.client.put(self.task_endpoint, payload)
        self.assertEqual(response.status_code, 204)

    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(**{"formKey": "zac:documentSelectie"}),
    )
    def test_put_user_task_no_permission(self, m, gt):
        user = UserFactory.create()
        self.client.force_authenticate(user)
        response = self.client.get(self.task_endpoint)
        self.assertEqual(response.status_code, 403)

    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(**{"formKey": "zac:validSign:configurePackage"}),
    )
    @patch("zac.camunda.api.views.complete_task", return_value=None)
    @patch(
        "zac.contrib.validsign.camunda.get_process_instance",
        return_value=None,
    )
    @patch(
        "zac.contrib.validsign.camunda.get_process_zaak_url",
        return_value=None,
    )
    def test_put_validsign_user_task(self, m, gt, ct, gpi, gpzu):
        self._mock_permissions(m)

        user = UserFactory.create(
            first_name="first_name",
            last_name="last_name",
            email="some@email.com",
        )
        payload = {
            "assigned_users": [{"username": user.username}],
            "selected_documents": [self.document.url],
        }

        with patch("zac.contrib.validsign.camunda.get_zaak", return_value=self.zaak):
            with patch(
                "zac.contrib.validsign.camunda.get_documenten",
                return_value=[[self.document], None],
            ):
                response = self.client.put(self.task_endpoint, payload)

        self.assertEqual(response.status_code, 204)
