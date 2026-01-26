import uuid
from pathlib import Path
from unittest.mock import PropertyMock, patch

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

import zac.core.camunda.start_process.serializers as start_serializers
from zac.accounts.tests.factories import BlueprintPermissionFactory, UserFactory
from zac.activities.tests.factories import ActivityFactory
from zac.api.context import ZaakContext
from zac.camunda.data import Task
from zac.contrib.objects.checklists.tests.factories import checklist_object_factory
from zac.contrib.objects.kownsl.constants import KownslTypes
from zac.contrib.objects.kownsl.tests.factories import (
    review_request_factory,
    reviews_factory,
)
from zac.contrib.objects.services import factory_review_request, factory_reviews
from zac.core.models import CoreConfig
from zac.core.permissions import zaakproces_usertasks
from zac.core.tests.utils import ClearCachesMixin
from zac.elasticsearch.api import create_informatieobject_document
from zac.tests import ServiceFactory
from zac.tests.compat import generate_oas_component, mock_service_oas_get
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
        ServiceFactory.create(
            api_type=APITypes.ztc,
            api_root=CATALOGI_ROOT,
        )
        ServiceFactory.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)
        ServiceFactory.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)

        cls.catalogus = generate_oas_component(
            "ztc",
            "schemas/Catalogus",
            url=f"{CATALOGI_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd",
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
                "waardenverzameling": [],
            },
            url=f"{CATALOGI_ROOT}eigenschappen/68b5b40c-c479-4008-a57b-a268b280df99",
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

        cls.zaak_dict = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7",
            zaaktype=cls.zaaktype["url"],
        )
        cls.zaakeigenschap = generate_oas_component(
            "zrc",
            "schemas/ZaakEigenschap",
            zaak=cls.zaak_dict["url"],
            eigenschap=cls.eigenschap["url"],
            naam=cls.eigenschap["naam"],
            waarde="bar",
        )
        cls.zaak = factory(Zaak, cls.zaak_dict)

        cls.document.last_edited_date = None  # avoid patching fetching audit trail
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

        cls.task_endpoint = reverse(
            "user-task-data", kwargs={"task_id": TASK_DATA["id"]}
        )

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.user)

        patchers = [
            patch(
                "zac.core.camunda.select_documents.context.get_process_zaak_url",
                return_value=self.zaak.url,
            ),
            patch(
                "zac.core.camunda.select_documents.context.get_zaaktype_from_identificatie",
                return_value=self.zaaktype_obj,
            ),
            patch(
                "zac.core.camunda.select_documents.context.get_informatieobjecttypen_for_zaaktype",
                return_value=[factory(InformatieObjectType, self.documenttype)],
            ),
            patch("django_camunda.api.get_client", return_value=_get_camunda_client()),
        ]

        for patcher in patchers:
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
    @patch(
        "zac.contrib.objects.kownsl.camunda.get_review_request_from_task",
        return_value=None,
    )
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
            "zac.contrib.objects.kownsl.camunda.get_zaak_context",
            return_value=self.zaak_context,
        ):
            with patch(
                "zac.contrib.objects.kownsl.camunda.get_zaakeigenschappen",
                return_value=[],
            ) as patch_get_zaakeigenschappen:
                response = self.client.get(self.task_endpoint)

        patch_get_zaakeigenschappen.assert_called_once()
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(sorted(list(data.keys())), sorted(["form", "task", "context"]))

        self.assertEqual(
            sorted(list(data["context"].keys())),
            sorted(
                [
                    "camundaAssignedUsers",
                    "zaakInformatie",
                    "zaakeigenschappen",
                    "title",
                    "documentsLink",
                    "reviewType",
                    "id",
                    "previouslyAssignedUsers",
                    "previouslySelectedDocuments",
                    "previouslySelectedZaakeigenschappen",
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
    @patch(
        "zac.contrib.objects.kownsl.camunda.get_review_request_from_task",
        return_value=None,
    )
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
            "zac.contrib.objects.kownsl.camunda.get_zaak_context",
            return_value=self.zaak_context,
        ):
            with patch(
                "zac.contrib.objects.kownsl.camunda.get_zaakeigenschappen",
                return_value=[],
            ) as patch_get_zaakeigenschappen:
                response = self.client.get(self.task_endpoint)

        patch_get_zaakeigenschappen.assert_called_once()
        data = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(sorted(list(data.keys())), sorted(["form", "task", "context"]))

        self.assertEqual(
            sorted(list(data["context"].keys())),
            sorted(
                [
                    "camundaAssignedUsers",
                    "zaakInformatie",
                    "zaakeigenschappen",
                    "title",
                    "documentsLink",
                    "reviewType",
                    "id",
                    "previouslyAssignedUsers",
                    "previouslySelectedDocuments",
                    "previouslySelectedZaakeigenschappen",
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
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        m.get(
            f"{CATALOGI_ROOT}eigenschappen?zaaktype={self.zaaktype['url']}",
            json=paginated_response([self.eigenschap]),
        )
        m.get(f"{self.zaak.url}/zaakeigenschappen", json=[self.zaakeigenschap])

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
        review_request_data = review_request_factory(
            assignedUsers=[
                {
                    "deadline": "2020-01-01",
                    "userAssignees": [
                        {
                            "username": user.username,
                            "firstName": user.first_name,
                            "lastName": user.last_name,
                            "fullName": user.get_full_name(),
                        }
                        for user in users
                    ],
                    "groupAssignees": [],
                    "emailNotification": False,
                },
            ],
            zaak=self.zaak.url,
            userDeadlines={
                "user:some-author": "2022-04-14",
                "user:some-other-author": "2022-04-15",
            },
            zaakeigenschappen=[self.zaakeigenschap["url"]],
            metadata={
                "taskDefinitionId": "submitAdvice",
                "processInstanceId": "6ebf534a-bc0a-11ec-a591-c69dd6a420a0",
            },
            requester={
                "username": "some-user",
                "firstName": "",
                "lastName": "",
                "fullName": "",
            },
        )

        review_request = factory_review_request(review_request_data)
        m.get(
            f"{CAMUNDA_URL}task/{TASK_DATA['id']}/variables/assignedUsers?deserializeValue=false",
            status_code=404,
        )

        with patch(
            "zac.contrib.objects.kownsl.camunda.search_informatieobjects",
            return_value=[self.document_es],
        ):
            with patch(
                "zac.contrib.objects.kownsl.camunda.get_zaak_context",
                return_value=self.zaak_context,
            ):
                with patch(
                    "zac.contrib.objects.kownsl.camunda.get_review_request_from_task",
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
                                "username": users[0].username,
                                "firstName": "",
                                "fullName": users[0].get_full_name(),
                                "lastName": "",
                            },
                            {
                                "username": users[1].username,
                                "firstName": "",
                                "fullName": users[1].get_full_name(),
                                "lastName": "",
                            },
                            {
                                "username": users[2].username,
                                "firstName": "",
                                "fullName": users[2].get_full_name(),
                                "lastName": "",
                            },
                        ],
                        "groupAssignees": [],
                        "emailNotification": False,
                        "deadline": "2020-01-01",
                    }
                ],
                "reviewType": "advice",
                "previouslySelectedDocuments": [],
                "previouslySelectedZaakeigenschappen": [self.zaakeigenschap["url"]],
                "title": f"{self.zaak_context.zaaktype.omschrijving} - {self.zaak_context.zaaktype.versiedatum}",
                "zaakInformatie": {
                    "omschrijving": self.zaak_context.zaak.omschrijving,
                    "toelichting": self.zaak_context.zaak.toelichting,
                },
                "zaakeigenschappen": [
                    {
                        "naam": self.eigenschap["naam"],
                        "waarde": self.zaakeigenschap["waarde"],
                        "url": self.zaakeigenschap["url"],
                    }
                ],
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
        reviews = factory_reviews(reviews_factory())
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
                            "zac.core.camunda.zet_resultaat.context.get_resultaattypen",
                            return_value=[factory(ResultaatType, resultaattype)],
                        ):
                            with patch(
                                "zac.core.camunda.zet_resultaat.context.get_reviews_for_zaak",
                                return_value=[reviews],
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

        drc = ServiceFactory.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)
        config = CoreConfig.get_solo()
        config.primary_drc = drc
        config.save()
        cls.document_dict = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            url=f"{DOCUMENTS_ROOT}enkelvoudiginformatieobject/e14e72de-56ba-42b6-be36-5c280e9b30cd",
        )

        cls.document = factory(Document, cls.document_dict)
        ServiceFactory.create(
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
        ServiceFactory.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7",
            zaaktype=cls.zaaktype["url"],
        )
        cls.zaak = factory(Zaak, zaak)

        cls.document.last_edited_date = None  # avoid patching fetching audit trail
        cls.document_es = create_informatieobject_document(cls.document)
        cls.zaak_context = ZaakContext(
            zaak=cls.zaak,
            zaaktype=cls.zaaktype_obj,
        )
        cls.task_endpoint = reverse(
            "user-task-data", kwargs={"task_id": TASK_DATA["id"]}
        )

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.user)
        patchers = [
            patch(
                "zac.core.camunda.select_documents.serializers.get_zaaktype_from_identificatie",
                return_value=self.zaaktype_obj,
            ),
            patch("django_camunda.api.get_client", return_value=_get_camunda_client()),
            patch(
                "zac.core.api.validators.search_informatieobjects",
                return_value=[self.document_es],
            ),
        ]
        for patcher in patchers:
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
            "documents": [self.document.url],
            "toelichting": "some-toelichting",
            "id": None,
        }
        rr = review_request_factory()
        review_request_data = review_request_factory(
            assignedUsers=[
                {
                    "deadline": "2020-01-01",
                    "userAssignees": [
                        {
                            "username": user.username,
                            "firstName": user.first_name,
                            "lastName": user.last_name,
                            "fullName": user.get_full_name(),
                        }
                        for user in users
                    ],
                    "groupAssignees": [],
                    "emailNotification": False,
                },
            ],
            zaak=self.zaak.url,
            userDeadlines={
                "user:some-author": "2022-04-14",
                "user:some-other-author": "2022-04-15",
            },
            metadata={
                "taskDefinitionId": "submitAdvice",
                "processInstanceId": "6ebf534a-bc0a-11ec-a591-c69dd6a420a0",
            },
            requester={
                "username": "some-user",
                "firstName": "",
                "lastName": "",
                "fullName": "",
            },
            documents=[self.document.url],
        )

        review_request = factory_review_request(rr)

        m.post(
            f"{CAMUNDA_URL}task/{TASK_DATA['id']}/assignee",
            status_code=201,
        )
        with patch(
            "zac.core.camunda.select_documents.serializers.get_zaak_context",
            return_value=self.zaak_context,
        ):
            with patch(
                "zac.contrib.objects.kownsl.camunda.get_zaak_context",
                return_value=self.zaak_context,
            ):
                with patch(
                    "zac.contrib.objects.kownsl.camunda.create_review_request",
                    return_value=review_request,
                ):
                    with patch(
                        "zac.contrib.objects.kownsl.cache.get_zaak",
                        return_value=self.zaak,
                    ) as mock_get_zaak:
                        response = self.client.put(self.task_endpoint, payload)

        mock_get_zaak.assert_called_once()
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
        rr = review_request_factory()
        review_request_data = review_request_factory(
            assignedUsers=[
                {
                    "deadline": "2020-01-01",
                    "userAssignees": [
                        {
                            "username": user.username,
                            "firstName": user.first_name,
                            "lastName": user.last_name,
                            "fullName": user.get_full_name(),
                        }
                        for user in users
                    ],
                    "groupAssignees": [],
                    "emailNotification": False,
                },
            ],
            zaak=self.zaak.url,
            userDeadlines={
                "user:some-author": "2022-04-14",
                "user:some-other-author": "2022-04-15",
            },
            metadata={
                "taskDefinitionId": "submitAdvice",
                "processInstanceId": "6ebf534a-bc0a-11ec-a591-c69dd6a420a0",
            },
            requester={
                "username": "some-user",
                "firstName": "",
                "lastName": "",
                "fullName": "",
            },
        )

        review_request = factory_review_request(rr)
        payload_assigned_users = [
            {
                "deadline": "2020-01-01",
                "userAssignees": [user.username for user in users],
                "groupAssignees": [],
                "emailNotification": False,
            },
        ]
        payload = {
            "id": rr["id"],
            "assignedUsers": payload_assigned_users,
            "toelichting": rr["toelichting"],
            "documents": [self.document.url],
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
                "zac.contrib.objects.kownsl.camunda.get_zaak_context",
                return_value=self.zaak_context,
            ):
                with patch(
                    "zac.contrib.objects.kownsl.camunda.get_review_request",
                    return_value=review_request,
                ):
                    with patch(
                        "zac.contrib.objects.kownsl.camunda.update_review_request",
                        return_value=review_request,
                    ) as purr:
                        with patch(
                            "zac.contrib.objects.kownsl.cache.get_zaak",
                            return_value=self.zaak,
                        ) as mock_get_zaak:
                            response = self.client.put(self.task_endpoint, payload)

        self.assertEqual(response.status_code, 204)
        purr.assert_called_once()
        mock_get_zaak.assert_called_once()

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
        "zac.core.services.get_rollen",
        return_value=[],
    )
    @patch(
        "zac.core.services.get_zaakeigenschappen",
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
        with patch.object(
            start_serializers.ConfigureZaakProcessSerializer,
            "zaakcontext",
            new_callable=PropertyMock,
        ) as zaak_context_mock:
            zaak_context_mock.return_value = self.zaak_context
            with patch(
                "zac.elasticsearch.searches.count_by_iot_in_zaak",
                return_value={self.document.informatieobjecttype.omschrijving: 1},
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

        rr = factory_review_request(
            review_request_factory(
                userDeadlines={
                    "user:some-author": "2022-04-14",
                }
            )
        )

        activity = ActivityFactory.create(zaak=self.zaak.url)
        checklist_object = checklist_object_factory()
        checklist_object["record"]["data"]["answers"][0] = {
            "answer": "",
            "question": "Ja?",
            "userAssignee": "some-user",
        }
        patch_get_zaak_context = patch(
            "zac.core.camunda.zet_resultaat.serializers.get_zaak_context",
            return_value=self.zaak_context,
        )
        patch_get_resultaattypen = patch(
            "zac.core.camunda.zet_resultaat.serializers.get_resultaattypen",
            return_value=[factory(ResultaatType, self.resultaattype)],
        )

        with patch_get_zaak_context as pgzc:
            with patch_get_resultaattypen as pgrt:
                response = self.client.put(self.task_endpoint, payload)
        self.assertEqual(response.status_code, 204)

        pgzc.assert_called()
        pgrt.assert_called()
