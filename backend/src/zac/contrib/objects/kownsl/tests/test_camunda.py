from datetime import date
from unittest.mock import MagicMock, patch

from django.contrib.sites.models import Site
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

import requests_mock
from django_camunda.utils import serialize_variable, underscoreize
from freezegun import freeze_time
from rest_framework import exceptions
from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import InformatieObjectType, ZaakType
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.constants import APITypes

from zac.accounts.tests.factories import GroupFactory, UserFactory
from zac.api.context import ZaakContext
from zac.camunda.data import Task
from zac.camunda.user_tasks import UserTaskData, get_context as _get_context
from zac.contrib.objects.kownsl.data import KownslTypes, ReviewRequest, Reviews
from zac.core.tests.utils import ClearCachesMixin
from zac.elasticsearch.api import create_informatieobject_document
from zac.tests import ServiceFactory
from zac.tests.compat import generate_oas_component, mock_service_oas_get
from zac.tests.utils import paginated_response
from zgw.models.zrc import Zaak

from ..camunda import (
    AssignedUsersSerializer,
    ConfigureReviewRequestSerializer,
    ReviewContextSerializer,
    ZaakInformatieTaskSerializer,
)
from .factories import (
    CATALOGI_ROOT,
    DOCUMENT_URL,
    DOCUMENTS_ROOT,
    ZAAK_URL,
    ZAKEN_ROOT,
    advice_factory,
    review_request_factory,
    reviews_factory,
)

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


class GetConfigureReviewRequestContextSerializersTests(ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        ServiceFactory.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)
        ServiceFactory.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        ServiceFactory.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)

        cls.catalogus = generate_oas_component(
            "ztc",
            "schemas/Catalogus",
            url=f"{CATALOGI_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd",
            domein="DOME",
        )
        cls.informatieobjecttype = generate_oas_component(
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
            url=DOCUMENT_URL,
            bestandsnaam="some-bestandsnaam.ext",
        )
        cls.document = factory(Document, document)
        cls.document.informatieobjecttype = factory(
            InformatieObjectType, cls.informatieobjecttype
        )

        cls.document.last_edited_date = None  # avoid patching fetching audit trail
        cls.document_es = create_informatieobject_document(cls.document)

        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/e13e72de-56ba-42b6-be36-5c280e9b30ce",
            catalogus=cls.catalogus["url"],
        )
        cls.zaaktype = factory(ZaakType, zaaktype)
        cls.eigenschap = generate_oas_component(
            "ztc",
            "schemas/Eigenschap",
            zaaktype=zaaktype["url"],
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
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=ZAAK_URL,
            zaaktype=zaaktype["url"],
        )
        cls.zaak = factory(Zaak, zaak)

        cls.zaakeigenschap = generate_oas_component(
            "zrc",
            "schemas/ZaakEigenschap",
            zaak=zaak["url"],
            eigenschap=cls.eigenschap["url"],
            naam=cls.eigenschap["naam"],
            waarde="bar",
        )
        cls.zaak_context = ZaakContext(
            zaak=cls.zaak,
            zaaktype=cls.zaaktype,
            documents_link=reverse(
                "zaak-documents-es",
                kwargs={
                    "bronorganisatie": cls.zaak.bronorganisatie,
                    "identificatie": cls.zaak.identificatie,
                },
            ),
        )
        cls.patch_get_zaak_context = patch(
            "zac.contrib.objects.kownsl.camunda.get_zaak_context",
            return_value=cls.zaak_context,
        )
        cls.task_endpoint = reverse(
            "user-task-data", kwargs={"task_id": TASK_DATA["id"]}
        )

    def setUp(self):
        super().setUp()

        self.patch_get_zaak_context.start()
        self.addCleanup(self.patch_get_zaak_context.stop)

    def test_zaak_informatie_task_serializer(self):
        # Sanity check
        serializer = ZaakInformatieTaskSerializer(self.zaak)
        self.assertEqual(
            sorted(list(serializer.data.keys())),
            sorted(["omschrijving", "toelichting"]),
        )
        self.assertEqual(
            serializer.data,
            {
                "omschrijving": self.zaak.omschrijving,
                "toelichting": self.zaak.toelichting,
            },
        )

    @requests_mock.Mocker()
    def test_advice_context_serializer(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        m.get(
            f"{CATALOGI_ROOT}eigenschappen?zaaktype={self.zaaktype.url}",
            json=paginated_response([self.eigenschap]),
        )
        m.get(f"{self.zaak.url}/zaakeigenschappen", json=[self.zaakeigenschap])

        task = _get_task(**{"formKey": "zac:configureAdviceRequest"})
        m.get(
            f"https://camunda.example.com/engine-rest/task/{TASK_DATA['id']}/variables/assignedUsers?deserializeValue=false",
            status_code=404,
        )
        with patch(
            "zac.contrib.objects.kownsl.camunda.get_review_request_from_task",
            return_value=None,
        ):
            task_data = UserTaskData(task=task, context=_get_context(task))
        serializer = ReviewContextSerializer(instance=task_data)
        self.assertEqual(
            {
                "camunda_assigned_users": {
                    "user_assignees": [],
                    "group_assignees": [],
                },
                "documents_link": reverse(
                    "zaak-documents-es",
                    kwargs={
                        "bronorganisatie": self.zaak.bronorganisatie,
                        "identificatie": self.zaak.identificatie,
                    },
                ),
                "zaakeigenschappen": [self.zaakeigenschap["url"]],
                "id": None,
                "previously_assigned_users": [],
                "review_type": KownslTypes.advice,
                "previously_selected_documents": [],
                "previously_selected_zaakeigenschappen": [],
                "title": f"{self.zaaktype.omschrijving} - {self.zaaktype.versiedatum}",
                "zaakeigenschappen": [
                    {
                        "url": self.zaakeigenschap["url"],
                        "waarde": self.zaakeigenschap["waarde"],
                        "naam": self.eigenschap["naam"],
                    }
                ],
                "zaak_informatie": {
                    "omschrijving": self.zaak.omschrijving,
                    "toelichting": self.zaak.toelichting,
                },
            },
            serializer.data["context"],
        )

    @requests_mock.Mocker()
    def test_approval_context_serializer(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")

        m.get(
            f"{CATALOGI_ROOT}eigenschappen?zaaktype={self.zaaktype.url}",
            json=paginated_response([]),
        )
        m.get(f"{self.zaak.url}/zaakeigenschappen", json=[])
        task = _get_task(**{"formKey": "zac:configureApprovalRequest"})
        group = GroupFactory.create(name="some-group")
        m.get(
            f"https://camunda.example.com/engine-rest/task/{TASK_DATA['id']}/variables/assignedUsers?deserializeValue=false",
            json=serialize_variable(["group:some-group"]),
        )
        with patch(
            "zac.contrib.objects.kownsl.camunda.get_review_request_from_task",
            return_value=None,
        ):
            task_data = UserTaskData(task=task, context=_get_context(task))
        serializer = ReviewContextSerializer(instance=task_data)
        self.assertEqual(
            serializer.data["context"],
            {
                "camunda_assigned_users": {
                    "user_assignees": [],
                    "group_assignees": [
                        {
                            "full_name": "Groep: some-group",
                            "name": "some-group",
                        }
                    ],
                },
                "documents_link": reverse(
                    "zaak-documents-es",
                    kwargs={
                        "bronorganisatie": self.zaak.bronorganisatie,
                        "identificatie": self.zaak.identificatie,
                    },
                ),
                "zaakeigenschappen": [],
                "id": None,
                "previously_assigned_users": [],
                "review_type": KownslTypes.approval,
                "previously_selected_documents": [],
                "previously_selected_zaakeigenschappen": [],
                "title": f"{self.zaaktype.omschrijving} - {self.zaaktype.versiedatum}",
                "zaak_informatie": {
                    "omschrijving": self.zaak.omschrijving,
                    "toelichting": self.zaak.toelichting,
                },
            },
        )

    @requests_mock.Mocker()
    def test_approval_context_serializer_with_user(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        m.get(
            f"{CATALOGI_ROOT}eigenschappen?zaaktype={self.zaaktype.url}",
            json=paginated_response([]),
        )
        m.get(f"{self.zaak.url}/zaakeigenschappen", json=[])

        task = _get_task(**{"formKey": "zac:configureApprovalRequest"})
        user = UserFactory.create(
            username="some-user", first_name="First", last_name="Last"
        )
        m.get(
            f"https://camunda.example.com/engine-rest/task/{TASK_DATA['id']}/variables/assignedUsers?deserializeValue=false",
            json=serialize_variable(["user:some-user"]),
        )
        with patch(
            "zac.contrib.objects.kownsl.camunda.get_review_request_from_task",
            return_value=None,
        ):
            task_data = UserTaskData(task=task, context=_get_context(task))
        serializer = ReviewContextSerializer(instance=task_data)
        self.assertEqual(
            serializer.data["context"],
            {
                "camunda_assigned_users": {
                    "user_assignees": [
                        {
                            "username": "some-user",
                            "full_name": user.get_full_name(),
                            "first_name": user.first_name,
                            "last_name": user.last_name,
                            "email": user.email,
                        }
                    ],
                    "group_assignees": [],
                },
                "documents_link": reverse(
                    "zaak-documents-es",
                    kwargs={
                        "bronorganisatie": self.zaak.bronorganisatie,
                        "identificatie": self.zaak.identificatie,
                    },
                ),
                "zaakeigenschappen": [],
                "id": None,
                "previously_assigned_users": [],
                "review_type": KownslTypes.approval,
                "previously_selected_documents": [],
                "previously_selected_zaakeigenschappen": [],
                "title": f"{self.zaaktype.omschrijving} - {self.zaaktype.versiedatum}",
                "zaak_informatie": {
                    "omschrijving": self.zaak.omschrijving,
                    "toelichting": self.zaak.toelichting,
                },
            },
        )

    @requests_mock.Mocker()
    def test_advice_context_serializer_previously_assigned_users(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        m.get(
            f"{CATALOGI_ROOT}eigenschappen?zaaktype={self.zaaktype.url}",
            json=paginated_response([]),
        )
        m.get(f"{self.zaak.url}/zaakeigenschappen", json=[])

        review_request = review_request_factory()

        task = _get_task(**{"formKey": "zac:configureAdviceRequest"})
        m.get(
            f"https://camunda.example.com/engine-rest/task/{TASK_DATA['id']}/variables/assignedUsers?deserializeValue=false",
            status_code=404,
        )
        m.get(
            f"https://camunda.example.com/engine-rest/task/{TASK_DATA['id']}/variables/kownslReviewRequestId?deserializeValue=false",
            json=serialize_variable(review_request["id"]),
        )

        # Let resolve_assignee get the right users and groups
        UserFactory.create(
            username=review_request["assignedUsers"][0]["userAssignees"][0]["username"]
        )
        UserFactory.create(
            username=review_request["assignedUsers"][1]["userAssignees"][0]["username"]
        )

        rr = factory(ReviewRequest, review_request)
        rr.documents = [self.document.url]

        # Avoid patching fetch_reviews and everything
        rr.reviews = []
        rr.fetched_reviews = True

        with patch(
            "zac.contrib.objects.kownsl.camunda.search_informatieobjects",
            return_value=[self.document_es],
        ):
            with patch(
                "zac.contrib.objects.kownsl.camunda.get_review_request_from_task",
                return_value=rr,
            ):
                task_data = UserTaskData(task=task, context=_get_context(task))
                serializer = ReviewContextSerializer(instance=task_data)
                self.assertEqual(
                    {
                        "camunda_assigned_users": {
                            "user_assignees": [],
                            "group_assignees": [],
                        },
                        "documents_link": reverse(
                            "zaak-documents-es",
                            kwargs={
                                "bronorganisatie": self.zaak.bronorganisatie,
                                "identificatie": self.zaak.identificatie,
                            },
                        ),
                        "zaakeigenschappen": [],
                        "id": review_request["id"],
                        "previously_assigned_users": [
                            {
                                "user_assignees": [
                                    {
                                        "email": "some-author@email.zac",
                                        "first_name": "Some First",
                                        "full_name": "Some First Some Last",
                                        "last_name": "Some Last",
                                        "username": "some-author",
                                    }
                                ],
                                "group_assignees": [],
                                "email_notification": False,
                                "deadline": "2022-04-14",
                            },
                            {
                                "user_assignees": [
                                    {
                                        "email": "some-other-author@email.zac",
                                        "first_name": "Some Other First",
                                        "full_name": "Some Other First Some Last",
                                        "last_name": "Some Last",
                                        "username": "some-other-author",
                                    }
                                ],
                                "group_assignees": [],
                                "email_notification": False,
                                "deadline": "2022-04-15",
                            },
                        ],
                        "review_type": KownslTypes.advice,
                        "previously_selected_documents": [self.document.url],
                        "previously_selected_zaakeigenschappen": [],
                        "title": f"{self.zaaktype.omschrijving} - {self.zaaktype.versiedatum}",
                        "zaak_informatie": {
                            "omschrijving": self.zaak.omschrijving,
                            "toelichting": self.zaak.toelichting,
                        },
                    },
                    serializer.data["context"],
                )


class ConfigureReviewRequestSerializersTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.users_1 = UserFactory.create_batch(3)
        cls.group = GroupFactory.create()
        cls.users_2 = UserFactory.create_batch(3)
        ServiceFactory.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)
        ServiceFactory.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        ServiceFactory.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)

        site = Site.objects.get_current()
        site.domain = "example"
        site.save()

        cls.catalogus = generate_oas_component(
            "ztc",
            "schemas/Catalogus",
            url=f"{CATALOGI_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd",
            domein="DOME",
        )
        cls.informatieobjecttype = generate_oas_component(
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
            url=DOCUMENT_URL,
            bestandsnaam="some-bestandsnaam.ext",
        )
        cls.document = factory(Document, document)
        cls.document.informatieobjecttype = factory(
            InformatieObjectType, cls.informatieobjecttype
        )

        cls.document.last_edited_date = None  # avoid patching fetching audit trail
        cls.document_es = create_informatieobject_document(cls.document)

        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=ZAAK_URL,
        )
        cls.zaak = factory(Zaak, zaak)
        cls.zaak_context = ZaakContext(
            zaak=cls.zaak,
        )
        cls.patch_get_zaak_context = patch(
            "zac.contrib.objects.kownsl.camunda.get_zaak_context",
            return_value=cls.zaak_context,
        )
        cls.patch_get_zaak_context_doc_ser = patch(
            "zac.core.camunda.select_documents.serializers.get_zaak_context",
            return_value=cls.zaak_context,
        )
        cls.patch_get_documenten = patch(
            "zac.core.api.validators.search_informatieobjects",
            return_value=[cls.document_es],
        )

        rr = review_request_factory(documents=[cls.document.url])

        # Let resolve_assignee get the right users and groups
        UserFactory.create(
            username=rr["assignedUsers"][0]["userAssignees"][0]["username"]
        )
        UserFactory.create(
            username=rr["assignedUsers"][1]["userAssignees"][0]["username"]
        )
        cls.review_request = factory(ReviewRequest, rr)
        cls.patch_create_review_request = patch(
            "zac.contrib.objects.kownsl.camunda.create_review_request",
            return_value=cls.review_request,
        )
        cls.task_endpoint = reverse(
            "user-task-data", kwargs={"task_id": TASK_DATA["id"]}
        )

    def setUp(self):
        super().setUp()

        self.patch_get_zaak_context.start()
        self.addCleanup(self.patch_get_zaak_context.stop)

        # self.patch_get_zaak_context_doc_ser.start()
        # self.addCleanup(self.patch_get_zaak_context_doc_ser.stop)

        self.patch_create_review_request.start()
        self.addCleanup(self.patch_create_review_request.stop)

        self.patch_get_documenten.start()
        self.addCleanup(self.patch_get_documenten.stop)

    @freeze_time("1999-12-31T23:59:59Z")
    def test_select_users_rev_req_serializer(self):
        # Sanity check
        payload = {
            "user_assignees": [user.username for user in self.users_1],
            "group_assignees": [self.group.name],
            "email_notification": False,
            "deadline": "2020-01-01",
        }
        serializer = AssignedUsersSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        # AssignedUsersSerializer returns AssignedUsers dataclass
        validated = serializer.validated_data
        self.assertEqual(validated.user_assignees, self.users_1)
        self.assertEqual(validated.group_assignees, [self.group])
        self.assertEqual(validated.email_notification, False)
        self.assertEqual(validated.deadline, date(2020, 1, 1))

    @freeze_time("1999-12-31T23:59:59Z")
    def test_select_users_rev_req_serializer_duplicate_users(self):
        payload = {
            "user_assignees": [user.username for user in self.users_1] * 2,
            "group_assignees": [self.group.name],
            "email_notification": False,
            "deadline": "2020-01-01",
        }
        serializer = AssignedUsersSerializer(data=payload)
        with self.assertRaisesMessage(
            exceptions.ValidationError, "Assigned users need to be unique."
        ):
            serializer.is_valid(raise_exception=True)

    @freeze_time("1999-12-31T23:59:59Z")
    def test_select_users_rev_req_serializer_date_error(self):
        payload = {
            "user_assignees": [user.username for user in self.users_1],
            "group_assignees": [self.group.name] * 2,
            "email_notification": False,
            "deadline": "2020-01-01",
        }
        serializer = AssignedUsersSerializer(data=payload)
        with self.assertRaisesMessage(
            exceptions.ValidationError, "Assigned groups need to be unique."
        ):
            serializer.is_valid(raise_exception=True)

    @freeze_time("1999-12-31T23:59:59Z")
    def test_select_assignees_rev_req_serializer_date_error(self):
        payload = {
            "user_assignees": [user.username for user in self.users_1],
            "group_assignees": [self.group.name],
            "email_notification": False,
            "deadline": "01-01-2010",
        }
        serializer = AssignedUsersSerializer(data=payload)
        with self.assertRaisesMessage(
            exceptions.ValidationError,
            "Date heeft het verkeerde formaat, gebruik 1 van deze formaten: YYYY-MM-DD.",
        ):
            serializer.is_valid(raise_exception=True)

    @freeze_time("1999-12-31T23:59:59Z")
    def test_configure_review_request_serializer(self):
        assigned_users = [
            {
                "user_assignees": [user.username for user in self.users_1],
                "group_assignees": [self.group.name],
                "email_notification": False,
                "deadline": "2020-01-01",
            },
            {
                "user_assignees": [user.username for user in self.users_2],
                "group_assignees": [],
                "email_notification": False,
                "deadline": "2020-01-02",
            },
        ]
        payload = {
            "assigned_users": assigned_users,
            "toelichting": "some-toelichting",
            "documents": [self.document.url],
            "id": None,
            "zaakeigenschappen": [],
        }

        task = _get_task(**{"formKey": "zac:configureAdviceRequest"})

        serializer = ConfigureReviewRequestSerializer(
            data=payload, context={"task": task}
        )
        self.assertTrue(serializer.is_valid(raise_exception=True))
        # AssignedUsersSerializer returns AssignedUsers dataclass instances
        validated_assigned_users = serializer.validated_data["assigned_users"]
        self.assertEqual(len(validated_assigned_users), 2)

        # Check first assigned users
        self.assertEqual(validated_assigned_users[0].user_assignees, self.users_1)
        self.assertEqual(validated_assigned_users[0].group_assignees, [self.group])
        self.assertEqual(validated_assigned_users[0].email_notification, False)
        self.assertEqual(validated_assigned_users[0].deadline, date(2020, 1, 1))

        # Check second assigned users
        self.assertEqual(validated_assigned_users[1].user_assignees, self.users_2)
        self.assertEqual(validated_assigned_users[1].group_assignees, [])
        self.assertEqual(validated_assigned_users[1].email_notification, False)
        self.assertEqual(validated_assigned_users[1].deadline, date(2020, 1, 2))

        self.assertEqual(serializer.validated_data["documents"], [self.document.url])
        self.assertEqual(serializer.validated_data["toelichting"], "some-toelichting")

    @freeze_time("1999-12-31T23:59:59Z")
    def test_configure_review_request_serializer_invalid_deadlines(self):
        assigned_users = [
            {
                "user_assignees": [user.username for user in self.users_1],
                "group_assignees": [self.group.name],
                "email_notification": False,
                "deadline": "2020-01-01",
            },
            {
                "user_assignees": [user.username for user in self.users_2],
                "group_assignees": [],
                "email_notification": False,
                "deadline": "2020-01-01",
            },
        ]
        payload = {
            "assigned_users": assigned_users,
            "toelichting": "some-toelichting",
            "documents": [self.document.url],
            "zaakeigenschappen": [],
        }

        task = _get_task(**{"formKey": "zac:configureAdviceRequest"})

        serializer = ConfigureReviewRequestSerializer(
            data=payload, context={"task": task}
        )
        with self.assertRaises(exceptions.ValidationError) as err:
            serializer.is_valid(raise_exception=True)
        self.assertEqual(err.exception.detail["assigned_users"][0].code, "invalid-date")

    @freeze_time("1999-12-31T23:59:59Z")
    def test_configure_review_request_serializer_empty_document(self):
        assigned_users = [
            {
                "user_assignees": [user.username for user in self.users_1],
                "group_assignees": [],
                "email_notification": False,
                "deadline": "2020-01-01",
            },
        ]
        payload = {
            "assigned_users": assigned_users,
            "toelichting": "some-toelichting",
            "documents": [],
            "zaakeigenschappen": [],
        }

        task = _get_task(**{"formKey": "zac:configureAdviceRequest"})

        serializer = ConfigureReviewRequestSerializer(
            data=payload, context={"task": task}
        )
        with self.assertRaises(exceptions.ValidationError) as err:
            serializer.is_valid(raise_exception=True)
        self.assertEqual(
            err.exception.detail["nonFieldErrors"][0],
            _("Select either documents or ZAAKEIGENSCHAPs."),
        )

    @freeze_time("1999-12-31T23:59:59Z")
    def test_configure_review_request_serializer_unique_users(self):
        assigned_users = [
            {
                "user_assignees": [user.username for user in self.users_1],
                "group_assignees": [],
                "email_notification": False,
                "deadline": "2020-01-01",
            },
            {
                "user_assignees": [user.username for user in self.users_1],
                "group_assignees": [],
                "email_notification": False,
                "deadline": "2020-01-02",
            },
        ]
        payload = {
            "assigned_users": assigned_users,
            "toelichting": "some-toelichting",
            "documents": [self.document.url],
            "zaakeigenschappen": [],
        }

        task = _get_task(**{"formKey": "zac:configureAdviceRequest"})

        serializer = ConfigureReviewRequestSerializer(
            data=payload, context={"task": task}
        )
        with self.assertRaises(exceptions.ValidationError) as err:
            serializer.is_valid(raise_exception=True)
        self.assertEqual(err.exception.detail["assigned_users"][0].code, "unique-users")

    @freeze_time("1999-12-31T23:59:59Z")
    def test_configure_review_request_serializer_empty_assignees(self):
        assigned_users = [
            {
                "user_assignees": [],
                "group_assignees": [],
                "deadline": "2020-01-01",
                "email_notification": False,
            },
        ]
        payload = {
            "assigned_users": assigned_users,
            "toelichting": "some-toelichting",
            "documents": [self.document.url],
            "zaakeigenschappen": [],
        }

        task = _get_task(**{"formKey": "zac:configureAdviceRequest"})

        serializer = ConfigureReviewRequestSerializer(
            data=payload, context={"task": task}
        )
        with self.assertRaisesMessage(
            exceptions.ValidationError, "You need to select either a user or a group."
        ):
            serializer.is_valid(raise_exception=True)

    @freeze_time("1999-12-31T23:59:59Z")
    def test_configure_review_request_serializer_get_process_variables(self):
        assigned_users = [
            {
                "user_assignees": [user.username for user in self.users_1],
                "group_assignees": [self.group.name],
                "email_notification": False,
                "deadline": "2020-01-01",
            },
        ]
        payload = {
            "assigned_users": assigned_users,
            "toelichting": "some-toelichting",
            "documents": [self.document.url],
            "id": None,
            "zaakeigenschappen": [],
        }

        task = _get_task(**{"formKey": "zac:configureAdviceRequest"})

        request = MagicMock()
        user = UserFactory.create()
        request.user = user
        serializer = ConfigureReviewRequestSerializer(
            data=payload, context={"task": task, "request": request}
        )
        serializer.is_valid(raise_exception=True)
        with patch("zac.contrib.objects.kownsl.cache.get_zaak", return_value=self.zaak):
            serializer.on_task_submission()
        self.assertTrue(hasattr(serializer, "review_request"))

        email_notification_list = {f"user:{user}": False for user in self.users_1}
        email_notification_list[f"group:{self.group}"] = False

        variables = serializer.get_process_variables()
        self.assertEqual(
            variables,
            {
                "kownslUsersList": [
                    [f"user:{user}" for user in self.users_1] + [f"group:{self.group}"]
                ],
                "kownslReviewRequestId": str(self.review_request.id),
                "kownslFrontendUrl": f"http://example/ui/kownsl/review-request/advice?uuid={self.review_request.id}",
                "emailNotificationList": email_notification_list,
            },
        )

    @freeze_time("1999-12-31T23:59:59Z")
    def test_configure_review_request_serializer_fail_get_process_variables(self):
        assigned_users = [
            {
                "user_assignees": [user.username for user in self.users_1],
                "group_assignees": [],
                "email_notification": False,
                "deadline": "2020-01-01",
            },
        ]
        payload = {
            "assigned_users": assigned_users,
            "toelichting": "some-toelichting",
            "documents": [self.document.url],
            "id": None,
            "zaakeigenschappen": [],
        }

        task = _get_task(**{"formKey": "zac:configureAdviceRequest"})

        request = MagicMock()
        user = UserFactory.create()
        request.user = user
        serializer = ConfigureReviewRequestSerializer(
            data=payload, context={"task": task, "request": request}
        )
        serializer.is_valid(raise_exception=True)
        with self.assertRaisesMessage(
            AssertionError,
            "Must call on_task_submission before getting process variables.",
        ) as err:
            serializer.get_process_variables()

    @freeze_time("1999-12-31T23:59:59Z")
    @requests_mock.Mocker()
    def test_reconfigure_review_request_serializer_user_already_reviewed(self, m):
        advice = advice_factory()
        review_request = review_request_factory(reviewType=KownslTypes.advice)
        reviews_advice = reviews_factory(
            reviews=[advice], reviewType=review_request["reviewType"]
        )
        user = UserFactory.create(username=advice["author"]["username"])
        assigned_users = [
            {
                "user_assignees": [user.username for user in self.users_1]
                + [user.username],
                "group_assignees": [self.group.name],
                "email_notification": False,
                "deadline": "2020-01-01",
            },
            {
                "user_assignees": [user.username for user in self.users_2],
                "group_assignees": [],
                "email_notification": False,
                "deadline": "2020-01-02",
            },
        ]
        payload = {
            "assigned_users": assigned_users,
            "toelichting": "some-toelichting",
            "documents": [self.document.url],
            "id": review_request["id"],
            "zaakeigenschappen": [],
        }

        task = _get_task(**{"formKey": "zac:configureAdviceRequest"})

        rr = factory(ReviewRequest, review_request)

        # Avoid patching fetch_reviews and everything
        rr.reviews = factory(Reviews, reviews_advice).reviews
        rr.fetched_reviews = True

        with patch(
            "zac.contrib.objects.kownsl.camunda.get_review_request",
            return_value=rr,
        ):
            serializer = ConfigureReviewRequestSerializer(
                data=payload, context={"task": task}
            )

            with self.assertRaises(ValidationError) as exc:
                serializer.is_valid(raise_exception=True)

        self.assertEqual(
            exc.exception.detail["nonFieldErrors"][0],
            "Gebruiker of groep heeft al geantwoord.",
        )
