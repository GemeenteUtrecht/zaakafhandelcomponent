import uuid
from datetime import date
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
from zac.api.context import ZaakContext
from zac.camunda.data import Task
from zac.camunda.user_tasks import UserTaskData, get_context as _get_context
from zac.contrib.dowc.constants import DocFileTypes
from zac.contrib.dowc.utils import get_dowc_url
from zac.contrib.kownsl.data import KownslTypes, ReviewRequest
from zac.core.utils import get_ui_url
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


class GetConfigureReviewRequestContextSerializersTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        Service.objects.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)
        document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
        )
        cls.document = factory(Document, document)

        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)

        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
        )

        cls.zaaktype = factory(ZaakType, zaaktype)

        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7",
            zaaktype=zaaktype["url"],
        )

        cls.zaak = factory(Zaak, zaak)

        cls.zaak_context = ZaakContext(
            zaak=cls.zaak,
            zaaktype=cls.zaaktype,
            documents=[
                cls.document,
            ],
        )

        cls.patch_get_zaak_context = patch(
            "zac.contrib.kownsl.camunda.get_zaak_context",
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

    def test_advice_context_serializer(self):
        task = _get_task(**{"formKey": "zac:configureAdviceRequest"})
        task_data = UserTaskData(task=task, context=_get_context(task))
        serializer = AdviceApprovalContextSerializer(instance=task_data)
        self.assertIn("context", serializer.data)
        self.assertEqual(
            sorted(list(serializer.data["context"].keys())),
            sorted(
                [
                    "documents",
                    "title",
                    "zaak_informatie",
                    "review_type",
                ]
            ),
        )
        self.assertEqual(
            serializer.data["context"],
            {
                "documents": [
                    {
                        "beschrijving": self.document.beschrijving,
                        "bestandsnaam": self.document.bestandsnaam,
                        "url": self.document.url,
                        "read_url": get_dowc_url(
                            self.document, purpose=DocFileTypes.read
                        ),
                    }
                ],
                "zaak_informatie": {
                    "omschrijving": self.zaak.omschrijving,
                    "toelichting": self.zaak.toelichting,
                },
                "title": f"{self.zaaktype.omschrijving} - {self.zaaktype.versiedatum}",
                "review_type": KownslTypes.advice,
            },
        )

    def test_approval_context_serializer(self):
        task = _get_task(**{"formKey": "zac:configureApprovalRequest"})
        task_data = UserTaskData(task=task, context=_get_context(task))
        serializer = AdviceApprovalContextSerializer(instance=task_data)
        self.assertIn("context", serializer.data)
        self.assertEqual(
            sorted(list(serializer.data["context"])),
            sorted(
                [
                    "documents",
                    "title",
                    "zaak_informatie",
                    "review_type",
                ]
            ),
        )
        self.assertEqual(
            serializer.data["context"],
            {
                "documents": [
                    {
                        "beschrijving": self.document.beschrijving,
                        "bestandsnaam": self.document.bestandsnaam,
                        "url": self.document.url,
                        "read_url": get_dowc_url(
                            self.document, purpose=DocFileTypes.read
                        ),
                    }
                ],
                "zaak_informatie": {
                    "omschrijving": self.zaak.omschrijving,
                    "toelichting": self.zaak.toelichting,
                },
                "title": f"{self.zaaktype.omschrijving} - {self.zaaktype.versiedatum}",
                "review_type": KownslTypes.approval,
            },
        )


class ConfigureReviewRequestSerializersTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.users_1 = UserFactory.create_batch(3)
        cls.users_2 = UserFactory.create_batch(3)

        Service.objects.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)
        document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
        )
        cls.document = factory(Document, document)

        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7",
        )

        cls.zaak = factory(Zaak, zaak)

        cls.zaak_context = ZaakContext(
            zaak=cls.zaak,
            documents=[
                cls.document,
            ],
        )

        cls.patch_get_zaak_context = patch(
            "zac.contrib.kownsl.camunda.get_zaak_context",
            return_value=cls.zaak_context,
        )

        cls.patch_get_zaak_context_doc_ser = patch(
            "zac.core.camunda.select_documents.serializers.get_zaak_context",
            return_value=cls.zaak_context,
        )

        cls.patch_get_documenten = patch(
            "zac.core.api.validators.get_documenten",
            return_value=([cls.document], []),
        )

        review_request_data = {
            "id": uuid.uuid4(),
            "created": "2020-01-01T15:15:22Z",
            "forZaak": cls.zaak.url,
            "reviewType": KownslTypes.advice,
            "documents": [cls.document],
            "frontendUrl": "http://some.kownsl.com/frontendurl/",
            "numAdvices": 0,
            "numApprovals": 1,
            "numAssignedUsers": 1,
            "toelichting": "some-toelichting",
            "userDeadlines": {},
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

        self.patch_get_zaak_context.start()
        self.addCleanup(self.patch_get_zaak_context.stop)

        self.patch_get_zaak_context_doc_ser.start()
        self.addCleanup(self.patch_get_zaak_context_doc_ser.stop)

        self.patch_create_review_request.start()
        self.addCleanup(self.patch_create_review_request.stop)

        self.patch_get_documenten.start()
        self.addCleanup(self.patch_get_documenten.stop)

    @freeze_time("1999-12-31T23:59:59Z")
    def test_select_users_rev_req_serializer(self):
        # Sanity check
        payload = {
            "users": [user.username for user in self.users_1],
            "deadline": "2020-01-01",
        }
        serializer = SelectUsersRevReqSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        self.assertEqual(
            sorted(list(serializer.validated_data.keys())),
            sorted(["users", "deadline"]),
        )
        self.assertEqual(
            serializer.validated_data,
            {
                "users": [user.username for user in self.users_1],
                "deadline": date(2020, 1, 1),
            },
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
        self.assertEqual(
            serializer.validated_data["assigned_users"],
            [
                {
                    "users": [user.username for user in self.users_1],
                    "deadline": date(2020, 1, 1),
                },
                {
                    "users": [user.username for user in self.users_2],
                    "deadline": date(2020, 1, 2),
                },
            ],
        )
        self.assertEqual(
            serializer.validated_data["selected_documents"], [self.document.url]
        )
        self.assertEqual(serializer.validated_data["toelichting"], "some-toelichting")

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
        self.assertEqual(err.exception.detail["assigned_users"][0].code, "invalid-date")

    @freeze_time("1999-12-31T23:59:59Z")
    def test_configure_review_request_serializer_empty_document(self):
        assigned_users = [
            {
                "users": [user.username for user in self.users_1],
                "deadline": "2020-01-01",
            },
        ]
        payload = {
            "assigned_users": assigned_users,
            "toelichting": "some-toelichting",
            "selected_documents": [""],
        }

        task = _get_task(**{"formKey": "zac:configureAdviceRequest"})

        serializer = ConfigureReviewRequestSerializer(
            data=payload, context={"task": task}
        )
        with self.assertRaises(exceptions.ValidationError) as err:
            serializer.is_valid(raise_exception=True)
        self.assertEqual(err.exception.detail["selected_documents"][0][0].code, "blank")

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
        self.assertEqual(
            sorted(list(variables.keys())),
            sorted(
                [
                    "kownslDocuments",
                    "kownslUsersList",
                    "kownslReviewRequestId",
                    "kownslFrontendUrl",
                ]
            ),
        )
        self.assertEqual(
            variables,
            {
                "kownslDocuments": serializer.validated_data["selected_documents"],
                "kownslUsersList": [[user.username for user in self.users_1]],
                "kownslReviewRequestId": str(self.review_request.id),
                "kownslFrontendUrl": get_ui_url(
                    [
                        "ui",
                        "kownsl",
                        "review-request",
                        self.review_request.review_type,
                    ],
                    params={"uuid": self.review_request.id},
                ),
            },
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
