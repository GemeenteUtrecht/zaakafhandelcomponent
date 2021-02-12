import uuid
from unittest.mock import MagicMock, patch

from django.urls import reverse

from django_camunda.utils import underscoreize
from freezegun import freeze_time
from rest_framework import exceptions
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component

from zac.accounts.tests.factories import UserFactory
from zac.camunda.data import Task
from zac.camunda.user_tasks import UserTaskData, get_context as _get_context
from zac.contrib.dowc.constants import DocFileTypes
from zac.contrib.kownsl.data import KownslTypes, ReviewRequest
from zgw.models.zrc import Zaak

from ..camunda import (
    AdviceApprovalContextSerializer,
    ConfigureReviewRequestSerializer,
    SelectUsersRevReqSerializer,
    ZaakInformatieTaskSerializer,
)

DOCUMENTS_ROOT = "http://documents.nl/api/v1/"
ZAKEN_ROOT = "http://zaken.nl/api/v1/"

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


class GetContextSerializersTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        Service.objects.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)
        document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
        )
        cls.document = factory(Document, document)

        cls.patch_get_documenten = patch(
            "zac.contrib.kownsl.camunda.get_documenten",
            return_value=([cls.document], None),
        )

        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)

        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
        )

        cls.zaaktype = factory(ZaakType, zaaktype)
        cls.patch_fetch_zaaktype = patch(
            "zac.contrib.kownsl.camunda.fetch_zaaktype", return_value=cls.zaaktype
        )

        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7",
            zaaktype=zaaktype["url"],
        )

        cls.zaak = factory(Zaak, zaak)
        cls.patch_get_zaak = patch(
            "zac.contrib.kownsl.camunda.get_zaak", return_value=cls.zaak
        )

        cls.patch_get_process_instance = patch(
            "zac.contrib.kownsl.camunda.get_process_instance",
            return_value=None,
        )
        cls.patch_get_process_zaak_url = patch(
            "zac.contrib.kownsl.camunda.get_process_zaak_url",
            return_value=None,
        )

        cls.task_endpoint = reverse(
            "user-task-data", kwargs={"task_id": TASK_DATA["id"]}
        )

    def setUp(self):
        super().setUp()

        self.patch_get_zaak.start()
        self.addCleanup(self.patch_get_zaak.stop)

        self.patch_fetch_zaaktype.start()
        self.addCleanup(self.patch_fetch_zaaktype.stop)

        self.patch_get_documenten.start()
        self.addCleanup(self.patch_get_documenten.stop)

        self.patch_get_process_instance.start()
        self.addCleanup(self.patch_get_process_instance.stop)

        self.patch_get_process_zaak_url.start()
        self.addCleanup(self.patch_get_process_zaak_url.stop)

    def test_zaak_informatie_task_serializer(self):
        # Sanity check
        serializer = ZaakInformatieTaskSerializer(self.zaak)
        self.assertTrue(
            all([field in serializer.data for field in ["omschrijving", "toelichting"]])
        )

    def test_advice_context_serializer(self):
        task = _get_task(**{"formKey": "zac:configureAdviceRequest"})
        task_data = UserTaskData(task=task, context=_get_context(task))
        serializer = AdviceApprovalContextSerializer(instance=task_data)
        self.assertIn("context", serializer.data)
        self.assertTrue(
            all(
                [
                    field in serializer.data["context"]
                    for field in [
                        "documents",
                        "title",
                        "zaak_informatie",
                        "review_type",
                    ]
                ]
            )
        )
        self.assertEqual(serializer.data["context"]["review_type"], KownslTypes.advice)

    def test_approval_context_serializer(self):
        task = _get_task(**{"formKey": "zac:configureApprovalRequest"})
        task_data = UserTaskData(task=task, context=_get_context(task))
        serializer = AdviceApprovalContextSerializer(instance=task_data)
        self.assertIn("context", serializer.data)
        self.assertTrue(
            all(
                [
                    field in serializer.data["context"]
                    for field in [
                        "documents",
                        "title",
                        "zaak_informatie",
                        "review_type",
                    ]
                ]
            )
        )
        self.assertEqual(
            serializer.data["context"]["review_type"], KownslTypes.approval
        )


class ConfigureReviewRequestSerializersTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.users_1 = UserFactory.create_batch(3)
        cls.users_2 = UserFactory.create_batch(3)

        # Patch get_process_instance
        cls.patch_get_process_instance = patch(
            "zac.contrib.kownsl.camunda.get_process_instance",
            return_value=None,
        )

        # Patch get_process_zaak_url
        cls.patch_get_process_zaak_url = patch(
            "zac.contrib.kownsl.camunda.get_process_zaak_url",
            return_value="",
        )

        # Patch get_zaak
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
        )
        cls.zaak = factory(Zaak, zaak)
        cls.patch_get_zaak = patch(
            "zac.contrib.kownsl.camunda.get_zaak", return_value=cls.zaak
        )

        # Patch get_documenten
        Service.objects.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)
        document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
        )
        cls.document = factory(Document, document)
        cls.patch_get_documenten = patch(
            "zac.contrib.kownsl.camunda.get_documenten",
            return_value=([cls.document], None),
        )

        review_request_data = {
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
        cls.review_request = factory(ReviewRequest, review_request_data)

        cls.patch_create_review_request = patch(
            "zac.contrib.kownsl.camunda.create_review_request",
            return_value=cls.review_request,
        )

        cls.task_endpoint = reverse(
            "user-task-data", kwargs={"task_id": TASK_DATA["id"]}
        )

    def setUp(self):
        super().setUp()

        self.patch_get_process_instance.start()
        self.addCleanup(self.patch_get_process_instance.stop)

        self.patch_get_process_zaak_url.start()
        self.addCleanup(self.patch_get_process_zaak_url.stop)

        self.patch_get_zaak.start()
        self.addCleanup(self.patch_get_zaak.stop)

        self.patch_get_documenten.start()
        self.addCleanup(self.patch_get_documenten.stop)

        self.patch_create_review_request.start()
        self.addCleanup(self.patch_create_review_request.stop)

    @freeze_time("1999-12-31T23:59:59Z")
    def test_select_users_rev_req_serializer(self):
        # Sanity check
        payload = {
            "users": [user.username for user in self.users_1],
            "deadline": "2020-01-01",
        }
        serializer = SelectUsersRevReqSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        self.assertTrue(
            all([field in serializer.data for field in ["users", "deadline"]])
        )

    @freeze_time("1999-12-31T23:59:59Z")
    def test_select_users_rev_req_serializer_duplicate_users(self):
        payload = {
            "users": [user.username for user in self.users_1] * 2,
            "deadline": "2020-01-01",
        }
        serializer = SelectUsersRevReqSerializer(data=payload)
        with self.assertRaisesMessage(
            exceptions.ValidationError, "Users need to be unique."
        ):
            serializer.is_valid(raise_exception=True)

    @freeze_time("1999-12-31T23:59:59Z")
    def test_select_users_rev_req_serializer_date_error(self):
        payload = {
            "users": [user.username for user in self.users_1],
            "deadline": "01-01-2010",
        }
        serializer = SelectUsersRevReqSerializer(data=payload)
        with self.assertRaisesMessage(
            exceptions.ValidationError,
            "Date heeft het verkeerde formaat, gebruik 1 van deze formaten: YYYY-MM-DD.",
        ):
            serializer.is_valid(raise_exception=True)

    @freeze_time("1999-12-31T23:59:59Z")
    def test_configure_review_request_serializer(self):
        assigned_users = [
            {
                "users": [user.username for user in self.users_1],
                "deadline": "2020-01-01",
            },
            {
                "users": [user.username for user in self.users_2],
                "deadline": "2020-01-02",
            },
        ]
        payload = {
            "assigned_users": assigned_users,
            "toelichting": "some-toelichting",
            "selected_documents": [self.document.url],
        }

        task = _get_task(**{"formKey": "zac:configureAdviceRequest"})

        serializer = ConfigureReviewRequestSerializer(
            data=payload, context={"task": task}
        )
        self.assertTrue(serializer.is_valid(raise_exception=True))

    @freeze_time("1999-12-31T23:59:59Z")
    def test_configure_review_request_serializer_invalid_deadlines(self):
        assigned_users = [
            {
                "users": [user.username for user in self.users_1],
                "deadline": "2020-01-01",
            },
            {
                "users": [user.username for user in self.users_2],
                "deadline": "2020-01-01",
            },
        ]
        payload = {
            "assigned_users": assigned_users,
            "toelichting": "some-toelichting",
            "selected_documents": [self.document.url],
        }

        task = _get_task(**{"formKey": "zac:configureAdviceRequest"})

        serializer = ConfigureReviewRequestSerializer(
            data=payload, context={"task": task}
        )
        with self.assertRaises(exceptions.ValidationError) as err:
            serializer.is_valid(raise_exception=True)
        self.assertEqual(err.exception.detail[0].code, "invalid-date")

    @freeze_time("1999-12-31T23:59:59Z")
    def test_configure_review_request_serializer_unique_users(self):
        assigned_users = [
            {
                "users": [user.username for user in self.users_1],
                "deadline": "2020-01-01",
            },
            {
                "users": [user.username for user in self.users_1],
                "deadline": "2020-01-02",
            },
        ]
        payload = {
            "assigned_users": assigned_users,
            "toelichting": "some-toelichting",
            "selected_documents": [self.document.url],
        }

        task = _get_task(**{"formKey": "zac:configureAdviceRequest"})

        serializer = ConfigureReviewRequestSerializer(
            data=payload, context={"task": task}
        )
        with self.assertRaises(exceptions.ValidationError) as err:
            serializer.is_valid(raise_exception=True)

        self.assertEqual(err.exception.detail["assigned_users"][0].code, "unique-users")

    @freeze_time("1999-12-31T23:59:59Z")
    def test_configure_review_request_serializer_empty_users(self):
        assigned_users = [
            {"users": [], "deadline": "2020-01-01"},
        ]
        payload = {
            "assigned_users": assigned_users,
            "toelichting": "some-toelichting",
            "selected_documents": [self.document.url],
        }

        task = _get_task(**{"formKey": "zac:configureAdviceRequest"})

        serializer = ConfigureReviewRequestSerializer(
            data=payload, context={"task": task}
        )
        with self.assertRaises(exceptions.ValidationError) as err:
            serializer.is_valid(raise_exception=True)

        self.assertEqual(err.exception.detail["assigned_users"][0].code, "empty-users")

    @freeze_time("1999-12-31T23:59:59Z")
    def test_configure_review_request_serializer_get_process_variables(self):
        assigned_users = [
            {
                "users": [user.username for user in self.users_1],
                "deadline": "2020-01-01",
            },
        ]
        payload = {
            "assigned_users": assigned_users,
            "toelichting": "some-toelichting",
            "selected_documents": [self.document.url],
        }

        task = _get_task(**{"formKey": "zac:configureAdviceRequest"})

        request = MagicMock()
        user = UserFactory.create()
        request.user = user
        serializer = ConfigureReviewRequestSerializer(
            data=payload, context={"task": task, "request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.on_task_submission()
        self.assertTrue(hasattr(serializer, "review_request"))
        variables = serializer.get_process_variables()
        self.assertTrue(
            all(
                [
                    field
                    in [
                        "kownslDocuments",
                        "kownslUsersList",
                        "kownslReviewRequestId",
                        "kownslFrontendUrl",
                    ]
                    for field in variables.keys()
                ]
            )
        )

    @freeze_time("1999-12-31T23:59:59Z")
    def test_configure_review_request_serializer_fail_get_process_variables(self):
        assigned_users = [
            {
                "users": [user.username for user in self.users_1],
                "deadline": "2020-01-01",
            },
        ]
        payload = {
            "assigned_users": assigned_users,
            "toelichting": "some-toelichting",
            "selected_documents": [self.document.url],
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
