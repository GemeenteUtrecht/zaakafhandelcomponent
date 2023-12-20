import uuid
from pathlib import Path
from unittest.mock import patch

from django.urls import reverse

import requests_mock
from django_camunda.client import get_client
from django_camunda.models import CamundaConfig
from django_camunda.utils import serialize_variable, underscoreize
from freezegun import freeze_time
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import (
    InformatieObjectType,
    ResultaatType,
    ZaakType,
)
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import BlueprintPermissionFactory, UserFactory
from zac.api.context import ZaakContext
from zac.camunda.data import Task
from zac.contrib.dowc.data import OpenDowc
from zac.contrib.kownsl.constants import KownslTypes
from zac.contrib.kownsl.data import ReviewRequest
from zac.core.models import CoreConfig
from zac.core.permissions import zaakproces_usertasks
from zac.core.tests.utils import ClearCachesMixin
from zac.elasticsearch.api import create_informatieobject_document, create_iot_document
from zac.tests.utils import mock_resource_get, paginated_response
from zgw.models.zrc import Zaak

DOCUMENTS_ROOT = "http://documents.nl/api/v1/"
ZAKEN_ROOT = "http://zaken.nl/api/v1/"
CATALOGI_ROOT = "https://open-zaak.nl/catalogi/api/v1/"
CAMUNDA_ROOT = "https://some.camunda.nl/"
CAMUNDA_API_PATH = "engine-rest/"
CAMUNDA_URL = f"{CAMUNDA_ROOT}{CAMUNDA_API_PATH}"


def _get_camunda_client():
    config = CamundaConfig.get_solo()
    config.root_url = CAMUNDA_ROOT
    config.rest_api_path = CAMUNDA_API_PATH
    config.save()
    return get_client()


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
class GetUserTaskContextViewTests(ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory.create()
        Service.objects.create(
            label="Catalogi API",
            api_type=APITypes.ztc,
            api_root=CATALOGI_ROOT,
        )
        Service.objects.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)

        cls.catalogus = generate_oas_component(
            "ztc",
            "schemas/Catalogus",
            url=f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd",
            domein="DOME",
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            catalogus=cls.catalogus["url"],
            url=f"{CATALOGI_ROOT}zaaktypen/d66790b7-8b01-4005-a4ba-8fcf2a60f21d",
            identificatie="ZT1",
            omschrijving="ZT1",
        )
        cls.zaaktype_obj = factory(ZaakType, cls.zaaktype)

        cls.documenttype = generate_oas_component(
            "ztc",
            "schemas/InformatieObjectType",
            url=f"{CATALOGI_ROOT}informatieobjecttypen/d5d7285d-ce95-4f9e-a36f-181f1c642aa6",
            omschrijving="bijlage",
            catalogus=cls.catalogus["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
        )
        document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            url=f"{DOCUMENTS_ROOT}enkelvoudiginformatieobject/e14e72de-56ba-42b6-be36-5c280e9b30cd",
            titel="some-titel",
            bestandsnaam="some-bestandsnaam.ext",
        )
        cls.document = factory(Document, document)
        cls.document.informatieobjecttype = factory(
            InformatieObjectType, cls.documenttype
        )

        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7",
            zaaktype=cls.zaaktype["url"],
        )
        cls.zaak = factory(Zaak, zaak)

        cls.document.last_edited_date = None
        cls.document_es = create_informatieobject_document(cls.document)

        cls.zaak_context = ZaakContext(
            zaak=cls.zaak,
            zaaktype=cls.zaaktype_obj,
            documents_link=reverse(
                "zaak-documents-es",
                kwargs={
                    "bronorganisatie": cls.zaak.bronorganisatie,
                    "identificatie": cls.zaak.identificatie,
                },
            ),
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
        cls.patch_get_camunda_client = [
            patch("django_camunda.api.get_client", return_value=_get_camunda_client())
        ]

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.user)

        self.patch_get_process_zaak_url.start()
        self.addCleanup(self.patch_get_process_zaak_url.stop)

        self.patch_get_zaaktype.start()
        self.addCleanup(self.patch_get_zaaktype.stop)

        self.patch_get_informatieobjecttypen_for_zaaktype.start()
        self.addCleanup(self.patch_get_informatieobjecttypen_for_zaaktype.stop)

        for patcher in self.patch_get_camunda_client:
            patcher.start()
            self.addCleanup(patcher.stop)

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
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        with patch(
            "zac.core.camunda.select_documents.context.get_zaak",
            return_value=self.zaak,
        ):
            response = self.client.get(self.task_endpoint)

        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(sorted(list(data.keys())), sorted(["form", "task", "context"]))
        self.assertIn("documentsLink", data["context"].keys())

    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(**{"formKey": "zac:configureAdviceRequest"}),
    )
    @patch("zac.contrib.kownsl.camunda.get_review_request_from_task", return_value=None)
    def test_get_configure_advice_review_request_context(self, m, gt, grr):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        m.get(
            f"{CAMUNDA_URL}task/{TASK_DATA['id']}/variables/assignedUsers?deserializeValue=false",
            status_code=404,
        )
        BlueprintPermissionFactory.create(
            role__permissions=[zaakproces_usertasks.name],
            for_user=self.user,
            policy={
                "catalogus": "DOME",
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
            sorted(
                [
                    "camundaAssignedUsers",
                    "zaakInformatie",
                    "title",
                    "documentsLink",
                    "reviewType",
                    "id",
                    "previouslyAssignedUsers",
                    "previouslySelectedDocuments",
                ]
            ),
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
    @patch("zac.contrib.kownsl.camunda.get_review_request_from_task", return_value=None)
    def test_get_configure_approval_review_request_context(self, m, gt, grr):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        m.get(
            f"{CAMUNDA_URL}task/{TASK_DATA['id']}/variables/assignedUsers?deserializeValue=false",
            status_code=404,
        )

        BlueprintPermissionFactory.create(
            role__permissions=[zaakproces_usertasks.name],
            for_user=self.user,
            policy={
                "catalogus": "DOME",
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
            sorted(
                [
                    "camundaAssignedUsers",
                    "zaakInformatie",
                    "title",
                    "documentsLink",
                    "reviewType",
                    "id",
                    "previouslyAssignedUsers",
                    "previouslySelectedDocuments",
                ]
            ),
        )

        self.assertEqual(data["context"]["reviewType"], KownslTypes.approval)
        self.assertEqual(
            sorted(list(data["context"]["zaakInformatie"].keys())),
            sorted(["omschrijving", "toelichting"]),
        )

    @freeze_time("1999-12-31T23:59:59Z")
    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(**{"formKey": "zac:configureAdviceRequest"}),
    )
    @patch("zac.camunda.api.views.set_assignee_and_complete_task", return_value=None)
    def test_get_reconfigure_advice_review_request_user_task(self, m, gt, ct):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        BlueprintPermissionFactory.create(
            role__permissions=[zaakproces_usertasks.name],
            for_user=self.user,
            policy={
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        users = UserFactory.create_batch(3)
        review_request_data = {
            "assignedUsers": [
                {
                    "deadline": "2020-01-01",
                    "user_assignees": [user.username for user in users],
                    "group_assignees": [],
                    "email_notification": False,
                },
            ],
            "created": "2022-04-14T15:49:09.830235Z",
            "id": "14aec7a0-06de-4b55-b839-a1c9a0415b46",
            "forZaak": self.zaak.url,
            "reviewType": KownslTypes.advice,
            "documents": [],
            "frontendUrl": "https://zac.cg-intern.utrecht.nl/ui/kownsl/14aec7a0-06de-4b55-b839-a1c9a0415b46/",
            "numAdvices": 1,
            "numApprovals": 0,
            "numAssignedUsers": 1,
            "openReviews": [
                {
                    "deadline": "2022-04-15",
                    "users": ["user:some-other-author"],
                    "groups": [],
                }
            ],
            "toelichting": "some-toelichting",
            "userDeadlines": {
                "user:some-author": "2022-04-14",
                "user:some-other-author": "2022-04-15",
            },
            "requester": {
                "username": "some-user",
                "firstName": "",
                "lastName": "",
                "fullName": "",
            },
            "metadata": {
                "taskDefinitionId": "submitAdvice",
                "processInstanceId": "6ebf534a-bc0a-11ec-a591-c69dd6a420a0",
            },
            "zaakDocuments": [],
            "reviews": [],
            "locked": False,
            "lockReason": "",
        }
        review_request = factory(ReviewRequest, review_request_data)
        m.get(
            f"{CAMUNDA_URL}task/{TASK_DATA['id']}/variables/assignedUsers?deserializeValue=false",
            status_code=404,
        )
        with patch(
            "zac.contrib.kownsl.camunda.get_zaak_context",
            return_value=self.zaak_context,
        ):
            with patch(
                "zac.contrib.kownsl.camunda.get_review_request_from_task",
                return_value=review_request,
            ):
                response = self.client.get(self.task_endpoint)

        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            data["context"],
            {
                "camundaAssignedUsers": {"userAssignees": [], "groupAssignees": []},
                "documentsLink": reverse(
                    "zaak-documents-es",
                    kwargs={
                        "bronorganisatie": self.zaak.bronorganisatie,
                        "identificatie": self.zaak.identificatie,
                    },
                ),
                "id": "14aec7a0-06de-4b55-b839-a1c9a0415b46",
                "previouslyAssignedUsers": [
                    {
                        "userAssignees": [
                            {
                                "id": users[0].id,
                                "username": users[0].username,
                                "firstName": "",
                                "fullName": users[0].get_full_name(),
                                "lastName": "",
                                "isStaff": False,
                                "email": users[0].email,
                                "groups": [],
                            },
                            {
                                "id": users[1].id,
                                "username": users[1].username,
                                "firstName": "",
                                "fullName": users[1].get_full_name(),
                                "lastName": "",
                                "isStaff": False,
                                "email": users[1].email,
                                "groups": [],
                            },
                            {
                                "id": users[2].id,
                                "username": users[2].username,
                                "firstName": "",
                                "fullName": users[2].get_full_name(),
                                "lastName": "",
                                "isStaff": False,
                                "email": users[2].email,
                                "groups": [],
                            },
                        ],
                        "groupAssignees": [],
                        "emailNotification": False,
                        "deadline": "2020-01-01",
                    }
                ],
                "reviewType": "advice",
                "previouslySelectedDocuments": [],
                "title": f"{self.zaak_context.zaaktype.omschrijving} - {self.zaak_context.zaaktype.versiedatum}",
                "zaakInformatie": {
                    "omschrijving": self.zaak_context.zaak.omschrijving,
                    "toelichting": self.zaak_context.zaak.toelichting,
                },
            },
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
                "catalogus": "DOME",
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
        self.assertIn("documentsLink", data["context"].keys())

    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(**{"formKey": "zac:startProcessForm"}),
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
                "catalogus": "DOME",
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
        self.assertIn("benodigdeBijlagen", data["context"].keys())
        self.assertIn("benodigdeRollen", data["context"].keys())
        self.assertIn("benodigdeZaakeigenschappen", data["context"].keys())

    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(**{"formKey": "zac:zetResultaat"}),
    )
    def test_get_zet_resultaat_context(self, m, *mocks):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        tasks = [_get_task(**{"formKey": "zac:zetResultaat"})]
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
        mock_resource_get(m, self.zaaktype)
        resultaattype = generate_oas_component(
            "ztc",
            "schemas/ResultaatType",
            catalogus=self.zaaktype["catalogus"],
        )
        m.get(
            f"{CAMUNDA_URL}task/598347ee-62fc-46a2-913a-6e0788bc1b8c/variables/resultaatTypeKeuzes?deserializeValue=false",
            json=serialize_variable([resultaattype["omschrijving"]]),
        )
        BlueprintPermissionFactory.create(
            role__permissions=[zaakproces_usertasks.name],
            for_user=self.user,
            policy={
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        with patch(
            "zac.core.camunda.zet_resultaat.context.check_document_status",
            return_value=[],
        ):
            with patch(
                "zac.core.camunda.zet_resultaat.context.get_process_zaak_url",
                return_value=self.zaak.url,
            ):
                with patch(
                    "zac.core.camunda.zet_resultaat.context.get_camunda_user_tasks_for_zaak",
                    return_value=tasks,
                ):
                    with patch(
                        "zac.core.camunda.zet_resultaat.context.get_zaak",
                        return_value=self.zaak,
                    ):
                        with patch(
                            "zac.core.camunda.zet_resultaat.context.get_all_review_requests_for_zaak",
                            return_value=[review_request],
                        ):
                            with patch(
                                "zac.core.camunda.zet_resultaat.context.get_resultaattypen",
                                return_value=[factory(ResultaatType, resultaattype)],
                            ):
                                response = self.client.get(self.task_endpoint)

        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(sorted(list(data.keys())), sorted(["form", "task", "context"]))
        self.assertIn("activiteiten", data["context"].keys())
        self.assertIn("checklistVragen", data["context"].keys())
        self.assertIn("taken", data["context"].keys())
        self.assertIn("verzoeken", data["context"].keys())
        self.assertIn("resultaattypen", data["context"].keys())
        self.assertIn("openDocumenten", data["context"].keys())


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
            url=f"{DOCUMENTS_ROOT}enkelvoudiginformatieobject/e14e72de-56ba-42b6-be36-5c280e9b30cd",
        )

        cls.document = factory(Document, cls.document_dict)
        Service.objects.create(
            label="Catalogi API",
            api_type=APITypes.ztc,
            api_root=CATALOGI_ROOT,
        )

        cls.catalogus = generate_oas_component(
            "ztc",
            "schemas/Catalogus",
            url=f"{CATALOGI_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd",
            domein="DOME",
        )
        cls.documenttype = generate_oas_component(
            "ztc",
            "schemas/InformatieObjectType",
            url=f"{CATALOGI_ROOT}informatieobjecttypen/d5d7285d-ce95-4f9e-a36f-181f1c642aa6",
            omschrijving="bijlage",
            catalogus=cls.catalogus["url"],
        )
        cls.resultaattype = generate_oas_component(
            "ztc", "schemas/ResultaatType", catalogus=cls.catalogus["url"]
        )

        cls.document.informatieobjecttype = factory(
            InformatieObjectType, cls.documenttype
        )

        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            catalogus=cls.catalogus["url"],
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

        cls.document.last_edited_date = None
        cls.document_es = create_informatieobject_document(cls.document)

        cls.patch_get_documenten_validator = patch(
            "zac.core.api.validators.search_informatieobjects",
            return_value=[cls.document_es],
        )

        cls.zaak_context = ZaakContext(
            zaak=cls.zaak,
            zaaktype=cls.zaaktype_obj,
        )

        cls.patch_fetch_zaaktype = patch(
            "zac.core.camunda.select_documents.serializers.get_zaaktype_from_identificatie",
            return_value=cls.zaaktype_obj,
        )
        cls.task_endpoint = reverse(
            "user-task-data", kwargs={"task_id": TASK_DATA["id"]}
        )
        cls.patch_get_camunda_client = [
            patch("django_camunda.api.get_client", return_value=_get_camunda_client())
        ]

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.user)

        self.patch_get_documenten_validator.start()
        self.addCleanup(self.patch_get_documenten_validator.stop)

        self.patch_fetch_zaaktype.start()
        self.addCleanup(self.patch_fetch_zaaktype.stop)

        for patcher in self.patch_get_camunda_client:
            patcher.start()
            self.addCleanup(patcher.stop)

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
                "catalogus": "DOME",
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
    @patch("zac.camunda.api.views.set_assignee_and_complete_task", return_value=None)
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
            f"{CAMUNDA_URL}process-instance/c6a5e447-c58e-4986-a30d-54fce7503bbf/variables/zaaktype?deserializeValues=false",
            json=serialize_variable(self.zaaktype["url"]),
        )
        m.get(
            f"{CAMUNDA_URL}process-instance/c6a5e447-c58e-4986-a30d-54fce7503bbf/variables/bronorganisatie?deserializeValues=false",
            json=serialize_variable("123456789"),
        )
        m.post(
            f"{CAMUNDA_URL}task/{TASK_DATA['id']}/assignee",
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
    @patch("zac.camunda.api.views.set_assignee_and_complete_task", return_value=None)
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
            "id": None,
        }
        review_request_data = {
            "assignedUsers": [
                {
                    "deadline": "2020-01-01",
                    "user_assignees": [user.username for user in users],
                    "group_assignees": [],
                    "email_notification": False,
                },
            ],
            "created": "2022-04-14T15:49:09.830235Z",
            "id": "14aec7a0-06de-4b55-b839-a1c9a0415b46",
            "forZaak": self.zaak.url,
            "reviewType": KownslTypes.advice,
            "documents": [],
            "frontendUrl": "https://zac.cg-intern.utrecht.nl/ui/kownsl/14aec7a0-06de-4b55-b839-a1c9a0415b46/",
            "numAdvices": 1,
            "numApprovals": 0,
            "numAssignedUsers": 1,
            "openReviews": [
                {
                    "deadline": "2022-04-15",
                    "users": ["user:some-other-author"],
                    "groups": [],
                }
            ],
            "toelichting": "some-toelichting",
            "userDeadlines": {
                "user:some-author": "2022-04-14",
                "user:some-other-author": "2022-04-15",
            },
            "requester": {
                "username": "some-user",
                "firstName": "",
                "lastName": "",
                "fullName": "",
            },
            "metadata": {
                "taskDefinitionId": "submitAdvice",
                "processInstanceId": "6ebf534a-bc0a-11ec-a591-c69dd6a420a0",
            },
            "zaakDocuments": [],
            "reviews": [],
            "locked": False,
            "lockReason": "",
        }
        review_request = factory(ReviewRequest, review_request_data)

        m.post(
            f"{CAMUNDA_URL}task/{TASK_DATA['id']}/assignee",
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

    @freeze_time("1999-12-31T23:59:59Z")
    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(**{"formKey": "zac:configureApprovalRequest"}),
    )
    @patch("zac.camunda.api.views.set_assignee_and_complete_task", return_value=None)
    def test_put_reconfigure_advice_review_request_user_task(self, m, gt, ct):
        self._mock_permissions(m)
        users = UserFactory.create_batch(3)
        review_request_data = {
            "assignedUsers": [
                {
                    "deadline": "2020-01-01",
                    "user_assignees": [user.username for user in users],
                    "group_assignees": [],
                    "email_notification": False,
                },
            ],
            "created": "2022-04-14T15:49:09.830235Z",
            "id": "14aec7a0-06de-4b55-b839-a1c9a0415b46",
            "forZaak": self.zaak.url,
            "reviewType": KownslTypes.advice,
            "documents": [],
            "frontendUrl": "https://zac.cg-intern.utrecht.nl/ui/kownsl/14aec7a0-06de-4b55-b839-a1c9a0415b46/",
            "numAdvices": 1,
            "numApprovals": 0,
            "numAssignedUsers": 1,
            "openReviews": [
                {
                    "deadline": "2022-04-15",
                    "users": ["user:some-other-author"],
                    "groups": [],
                }
            ],
            "toelichting": "some-toelichting",
            "userDeadlines": {
                "user:some-author": "2022-04-14",
                "user:some-other-author": "2022-04-15",
            },
            "requester": {
                "username": "some-user",
                "firstName": "",
                "lastName": "",
                "fullName": "",
            },
            "metadata": {
                "taskDefinitionId": "submitAdvice",
                "processInstanceId": "6ebf534a-bc0a-11ec-a591-c69dd6a420a0",
            },
            "zaakDocuments": [],
            "reviews": [],
            "locked": False,
            "lockReason": "",
        }
        review_request = factory(ReviewRequest, review_request_data)
        payload = {
            "id": review_request_data["id"],
            "assignedUsers": review_request_data["assignedUsers"],
            "toelichting": review_request_data["toelichting"],
            "selectedDocuments": [],
        }

        m.post(
            f"{CAMUNDA_URL}task/{TASK_DATA['id']}/assignee",
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
                    "zac.contrib.kownsl.camunda.get_review_request",
                    return_value=review_request,
                ):
                    with patch(
                        "zac.contrib.kownsl.camunda.retrieve_advices",
                        return_value=[],
                    ) as radv:
                        with patch(
                            "zac.contrib.kownsl.camunda.retrieve_approvals",
                            return_value=[],
                        ) as rapp:
                            with patch(
                                "zac.contrib.kownsl.camunda.update_assigned_users_review_request",
                                return_value=review_request,
                            ) as purr:
                                response = self.client.put(self.task_endpoint, payload)

        self.assertEqual(response.status_code, 204)
        purr.assert_called_once()
        rapp.assert_not_called()
        radv.assert_called()

    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(**{"formKey": "zac:validSign:configurePackage"}),
    )
    @patch("zac.camunda.api.views.set_assignee_and_complete_task", return_value=None)
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
            f"{CAMUNDA_URL}task/{TASK_DATA['id']}/assignee",
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
    @patch("zac.camunda.api.views.set_assignee_and_complete_task", return_value=None)
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
            f"{CAMUNDA_URL}process-definition/aProcDefId/xml",
            headers={"Content-Type": "application/json"},
            json=response,
        )
        m.post(
            f"{CAMUNDA_URL}task/{TASK_DATA['id']}/assignee",
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
    @patch("zac.camunda.api.views.set_assignee_and_complete_task", return_value=None)
    def test_put_empty_formkey_user_task(self, m, mock_get_task, mock_complete_task):
        FILES_DIR = Path(__file__).parent / "files"

        with open(FILES_DIR / "keuze-form.bpmn", "r") as bpmn:
            response = {
                "id": "aProcDefId",
                "bpmn20Xml": bpmn.read(),
            }
        m.get(
            f"{CAMUNDA_URL}process-definition/aProcDefId/xml",
            headers={"Content-Type": "application/json"},
            json=response,
        )
        m.post(
            f"{CAMUNDA_URL}task/{TASK_DATA['id']}/assignee",
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
    @patch("zac.camunda.api.views.set_assignee_and_complete_task", return_value=None)
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
    def test_put_configure_zaak_process_user_task(self, m, *mocks):
        self._mock_permissions(m)
        payload = {}

        m.post(
            f"{CAMUNDA_URL}task/{TASK_DATA['id']}/assignee",
            status_code=201,
        )
        with patch(
            "zac.core.camunda.start_process.serializers.get_zaak_context",
            return_value=self.zaak_context,
        ):
            with patch(
                "zac.core.camunda.start_process.serializers.resolve_documenten_informatieobjecttypen",
                return_value=[self.document_es],
            ):
                with patch(
                    "zac.core.camunda.start_process.serializers.ConfigureZaakProcessSerializer.validate_bijlagen",
                    return_value=[self.document_es],
                ):
                    response = self.client.put(self.task_endpoint, payload)
        self.assertEqual(response.status_code, 204)

    @patch(
        "zac.camunda.api.views.get_task",
        return_value=_get_task(**{"formKey": "zac:zetResultaat"}),
    )
    @patch("zac.camunda.api.views.set_assignee_and_complete_task", return_value=None)
    def test_put_zet_resultaat_user_task(self, m, *mocks):
        self._mock_permissions(m)
        payload = {"resultaat": self.resultaattype["omschrijving"]}
        _uuid = uuid.uuid4()
        m.post(
            f"{CAMUNDA_URL}task/{TASK_DATA['id']}/assignee",
            status_code=201,
        )
        with patch(
            "zac.core.camunda.zet_resultaat.serializers.check_document_status",
            return_value=factory(
                OpenDowc, [{"document": self.document.url, "uuid": str(_uuid)}]
            ),
        ):
            with patch(
                "zac.core.camunda.zet_resultaat.serializers.patch_and_destroy_doc",
                return_value={"some-key": "some-value"},
            ) as patch_and_destroy_doc:
                with patch(
                    "zac.core.camunda.zet_resultaat.serializers.get_zaak_context",
                    return_value=self.zaak_context,
                ):
                    with patch(
                        "zac.core.camunda.zet_resultaat.serializers.get_resultaattypen",
                        return_value=[factory(ResultaatType, self.resultaattype)],
                    ):
                        response = self.client.put(self.task_endpoint, payload)
        self.assertEqual(response.status_code, 204)
        patch_and_destroy_doc.assert_called_once_with(str(_uuid), force=True)
