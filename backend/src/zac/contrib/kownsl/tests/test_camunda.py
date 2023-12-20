from copy import deepcopy
from datetime import date
from unittest.mock import MagicMock, patch

from django.urls import reverse

import requests_mock
from django_camunda.utils import serialize_variable, underscoreize
from freezegun import freeze_time
from rest_framework import exceptions
from rest_framework.exceptions import ValidationError
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import GroupFactory, UserFactory
from zac.api.context import ZaakContext
from zac.camunda.data import Task
from zac.camunda.user_tasks import UserTaskData, get_context as _get_context
from zac.contrib.kownsl.data import KownslTypes, ReviewRequest
from zac.core.tests.utils import ClearCachesMixin
from zgw.models.zrc import Zaak

from ..camunda import (
    AdviceApprovalContextSerializer,
    ConfigureReviewRequestSerializer,
    WriteAssignedUsersSerializer,
    ZaakInformatieTaskSerializer,
)
from ..models import KownslConfig
from .utils import (
    ADVICE,
    DOCUMENT_URL,
    DOCUMENTS_ROOT,
    KOWNSL_ROOT,
    REVIEW_REQUEST,
    ZAAK_URL,
    ZAKEN_ROOT,
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
        cls.maxDiff = None
        super().setUpTestData()
        Service.objects.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)
        document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            url=DOCUMENT_URL,
            bestandsnaam="some-bestandsnaam.ext",
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
            url=ZAAK_URL,
            zaaktype=zaaktype["url"],
        )
        cls.zaak = factory(Zaak, zaak)
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
            "zac.contrib.kownsl.camunda.get_zaak_context",
            return_value=cls.zaak_context,
        )
        cls.task_endpoint = reverse(
            "user-task-data", kwargs={"task_id": TASK_DATA["id"]}
        )

        cls.patch_search_informatieobjects = patch(
            "zac.contrib.kownsl.camunda.search_informatieobjects",
            return_value=[cls.document],
        )

    def setUp(self):
        super().setUp()

        self.patch_get_zaak_context.start()
        self.addCleanup(self.patch_get_zaak_context.stop)

        self.patch_search_informatieobjects.start()
        self.addCleanup(self.patch_search_informatieobjects.stop)

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
        task = _get_task(**{"formKey": "zac:configureAdviceRequest"})
        m.get(
            f"https://camunda.example.com/engine-rest/task/{TASK_DATA['id']}/variables/assignedUsers?deserializeValue=false",
            status_code=404,
        )
        with patch(
            "zac.contrib.kownsl.camunda.get_review_request_from_task", return_value=None
        ):
            task_data = UserTaskData(task=task, context=_get_context(task))
        serializer = AdviceApprovalContextSerializer(instance=task_data)

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
                "id": None,
                "previously_assigned_users": [],
                "review_type": KownslTypes.advice,
                "previously_selected_documents": [],
                "title": f"{self.zaaktype.omschrijving} - {self.zaaktype.versiedatum}",
                "zaak_informatie": {
                    "omschrijving": self.zaak.omschrijving,
                    "toelichting": self.zaak.toelichting,
                },
            },
            serializer.data["context"],
        )

    @requests_mock.Mocker()
    def test_approval_context_serializer(self, m):
        task = _get_task(**{"formKey": "zac:configureApprovalRequest"})
        group = GroupFactory.create(name="some-group")
        m.get(
            f"https://camunda.example.com/engine-rest/task/{TASK_DATA['id']}/variables/assignedUsers?deserializeValue=false",
            json=serialize_variable(["group:some-group"]),
        )
        with patch(
            "zac.contrib.kownsl.camunda.get_review_request_from_task", return_value=None
        ):
            task_data = UserTaskData(task=task, context=_get_context(task))
        serializer = AdviceApprovalContextSerializer(instance=task_data)
        self.assertEqual(
            serializer.data["context"],
            {
                "camunda_assigned_users": {
                    "user_assignees": [],
                    "group_assignees": [
                        {
                            "full_name": "Groep: some-group",
                            "name": "some-group",
                            "id": group.id,
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
                "id": None,
                "previously_assigned_users": [],
                "review_type": KownslTypes.approval,
                "previously_selected_documents": [],
                "title": f"{self.zaaktype.omschrijving} - {self.zaaktype.versiedatum}",
                "zaak_informatie": {
                    "omschrijving": self.zaak.omschrijving,
                    "toelichting": self.zaak.toelichting,
                },
            },
        )

    @requests_mock.Mocker()
    def test_approval_context_serializer_with_user(self, m):
        task = _get_task(**{"formKey": "zac:configureApprovalRequest"})
        user = UserFactory.create(
            username="some-user", first_name="First", last_name="Last"
        )
        m.get(
            f"https://camunda.example.com/engine-rest/task/{TASK_DATA['id']}/variables/assignedUsers?deserializeValue=false",
            json=serialize_variable(["user:some-user"]),
        )
        with patch(
            "zac.contrib.kownsl.camunda.get_review_request_from_task", return_value=None
        ):
            task_data = UserTaskData(task=task, context=_get_context(task))
        serializer = AdviceApprovalContextSerializer(instance=task_data)
        self.assertEqual(
            serializer.data["context"],
            {
                "camunda_assigned_users": {
                    "user_assignees": [
                        {
                            "username": "some-user",
                            "full_name": user.get_full_name(),
                            "id": user.id,
                            "first_name": user.first_name,
                            "last_name": user.last_name,
                            "is_staff": user.is_staff,
                            "email": user.email,
                            "groups": [],
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
                "id": None,
                "previously_assigned_users": [],
                "review_type": KownslTypes.approval,
                "previously_selected_documents": [],
                "title": f"{self.zaaktype.omschrijving} - {self.zaaktype.versiedatum}",
                "zaak_informatie": {
                    "omschrijving": self.zaak.omschrijving,
                    "toelichting": self.zaak.toelichting,
                },
            },
        )

    @requests_mock.Mocker()
    def test_advice_context_serializer_previously_assigned_users(self, m):
        task = _get_task(**{"formKey": "zac:configureAdviceRequest"})
        m.get(
            f"https://camunda.example.com/engine-rest/task/{TASK_DATA['id']}/variables/assignedUsers?deserializeValue=false",
            status_code=404,
        )
        m.get(
            f"https://camunda.example.com/engine-rest/task/{TASK_DATA['id']}/variables/kownslReviewRequestId?deserializeValue=false",
            json=serialize_variable(REVIEW_REQUEST["id"]),
        )

        service = Service.objects.create(
            label="Kownsl",
            api_type=APITypes.orc,
            api_root=KOWNSL_ROOT,
            auth_type=AuthTypes.zgw,
            client_id="zac",
            secret="supersecret",
            user_id="zac",
        )
        config = KownslConfig.get_solo()
        config.service = service
        config.save()
        mock_service_oas_get(m, KOWNSL_ROOT, "kownsl")
        m.get(
            f"{KOWNSL_ROOT}api/v1/review-requests/{REVIEW_REQUEST['id']}",
            json=REVIEW_REQUEST,
        )
        m.get(
            f"{KOWNSL_ROOT}api/v1/review-requests/{REVIEW_REQUEST['id']}/advices",
            json=[ADVICE],
        )
        # Let resolve_assignee get the right users and groups
        UserFactory.create(
            username=REVIEW_REQUEST["assignedUsers"][0]["user_assignees"][0]
        )
        UserFactory.create(
            username=REVIEW_REQUEST["assignedUsers"][1]["user_assignees"][0]
        )

        user = UserFactory.create(username="some-other-author")
        task_data = UserTaskData(task=task, context=_get_context(task))
        serializer = AdviceApprovalContextSerializer(instance=task_data)
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
                "id": REVIEW_REQUEST["id"],
                "previously_assigned_users": [
                    {
                        "user_assignees": [
                            {
                                "id": user.id,
                                "username": user.username,
                                "first_name": user.first_name,
                                "full_name": user.get_full_name(),
                                "last_name": user.last_name,
                                "is_staff": user.is_staff,
                                "email": user.email,
                                "groups": [],
                            }
                        ],
                        "group_assignees": [],
                        "email_notification": False,
                        "deadline": "2022-04-15",
                    }
                ],
                "review_type": KownslTypes.advice,
                "previously_selected_documents": [],
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
        Service.objects.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)
        document = generate_oas_component(
            "drc", "schemas/EnkelvoudigInformatieObject", url=DOCUMENT_URL
        )
        cls.document = factory(Document, document)
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=ZAAK_URL,
        )
        cls.zaak = factory(Zaak, zaak)
        cls.zaak_context = ZaakContext(
            zaak=cls.zaak,
        )
        cls.patch_search_informatieobjects = patch(
            "zac.contrib.kownsl.camunda.search_informatieobjects",
            return_value=[cls.document],
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
            "zac.core.api.validators.search_informatieobjects",
            return_value=[cls.document],
        )
        rr = deepcopy(REVIEW_REQUEST)
        rr["documents"] = [cls.document.url]

        # Let resolve_assignee get the right users and groups
        UserFactory.create(username=rr["assignedUsers"][0]["user_assignees"][0])
        UserFactory.create(username=rr["assignedUsers"][1]["user_assignees"][0])
        cls.review_request = factory(ReviewRequest, rr)
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

        self.patch_search_informatieobjects.start()
        self.addCleanup(self.patch_search_informatieobjects.stop)

    @freeze_time("1999-12-31T23:59:59Z")
    def test_select_users_rev_req_serializer(self):
        # Sanity check
        payload = {
            "user_assignees": [user.username for user in self.users_1],
            "group_assignees": [self.group.name],
            "email_notification": False,
            "deadline": "2020-01-01",
        }
        serializer = WriteAssignedUsersSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        self.assertEqual(
            sorted(list(serializer.validated_data.keys())),
            sorted(
                ["user_assignees", "group_assignees", "deadline", "email_notification"]
            ),
        )
        self.assertEqual(
            serializer.validated_data,
            {
                "user_assignees": self.users_1,
                "group_assignees": [self.group],
                "email_notification": False,
                "deadline": date(2020, 1, 1),
            },
        )

    @freeze_time("1999-12-31T23:59:59Z")
    def test_select_users_rev_req_serializer_duplicate_users(self):
        payload = {
            "user_assignees": [user.username for user in self.users_1] * 2,
            "group_assignees": [self.group.name],
            "email_notification": False,
            "deadline": "2020-01-01",
        }
        serializer = WriteAssignedUsersSerializer(data=payload)
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
        serializer = WriteAssignedUsersSerializer(data=payload)
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
        serializer = WriteAssignedUsersSerializer(data=payload)
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
            "selected_documents": [self.document.url],
            "id": None,
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
                    "user_assignees": self.users_1,
                    "group_assignees": [self.group],
                    "email_notification": False,
                    "deadline": date(2020, 1, 1),
                },
                {
                    "user_assignees": self.users_2,
                    "group_assignees": [],
                    "email_notification": False,
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
                "user_assignees": [user.username for user in self.users_1],
                "group_assignees": [],
                "email_notification": False,
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
            "selected_documents": [self.document.url],
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
            "selected_documents": [self.document.url],
            "id": None,
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

        email_notification_list = {f"user:{user}": False for user in self.users_1}
        email_notification_list[f"group:{self.group}"] = False

        variables = serializer.get_process_variables()
        self.assertEqual(
            variables,
            {
                "kownslDocuments": serializer.validated_data["selected_documents"],
                "kownslUsersList": [
                    [f"user:{user}" for user in self.users_1] + [f"group:{self.group}"]
                ],
                "kownslReviewRequestId": str(self.review_request.id),
                "kownslFrontendUrl": f"http://example.com/ui/kownsl/review-request/advice?uuid={self.review_request.id}",
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
            "selected_documents": [self.document.url],
            "id": None,
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
        service = Service.objects.create(
            label="Kownsl",
            api_type=APITypes.orc,
            api_root=KOWNSL_ROOT,
            auth_type=AuthTypes.zgw,
            client_id="zac",
            secret="supersecret",
            user_id="zac",
        )
        config = KownslConfig.get_solo()
        config.service = service
        config.save()
        mock_service_oas_get(m, KOWNSL_ROOT, "kownsl")
        m.get(
            f"{KOWNSL_ROOT}api/v1/review-requests/{REVIEW_REQUEST['id']}",
            json=REVIEW_REQUEST,
        )
        m.get(
            f"{KOWNSL_ROOT}api/v1/review-requests/{REVIEW_REQUEST['id']}/advices",
            json=[ADVICE],
        )
        user = UserFactory.create(username=ADVICE["author"]["username"])
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
            "selected_documents": [self.document.url],
            "id": REVIEW_REQUEST["id"],
        }

        task = _get_task(**{"formKey": "zac:configureAdviceRequest"})

        serializer = ConfigureReviewRequestSerializer(
            data=payload, context={"task": task}
        )

        with self.assertRaises(ValidationError) as exc:
            serializer.is_valid(raise_exception=True)

        self.assertEqual(
            exc.exception.detail["non_field_errors"][0],
            "User or group already reviewed.",
        )
