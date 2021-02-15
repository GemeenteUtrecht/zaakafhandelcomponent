import uuid
from unittest.mock import MagicMock, patch

from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from django_camunda.utils import underscoreize
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
from zac.contrib.kownsl.data import KownslTypes, ReviewRequest
from zgw.models.zrc import Zaak

from ..camunda import (
    ValidSignContextSerializer,
    ValidSignTaskSerializer,
    ValidSignUserSerializer,
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


class GetValidSignContextSerializersTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

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
            "zac.contrib.validsign.camunda.get_zaak_context",
            return_value=cls.zaak_context,
        )

        cls.task_endpoint = reverse(
            "user-task-data", kwargs={"task_id": TASK_DATA["id"]}
        )

    def setUp(self):
        super().setUp()

        self.patch_get_zaak_context.start()
        self.addCleanup(self.patch_get_zaak_context.stop)

    def test_valid_sign_context_serializer(self):
        task = _get_task(**{"formKey": "zac:validSign:configurePackage"})
        task_data = UserTaskData(task=task, context=_get_context(task))
        serializer = ValidSignContextSerializer(instance=task_data)
        self.assertIn("context", serializer.data)
        self.assertIn("documents", serializer.data["context"])
        self.assertEqual(len(serializer.data["context"]["documents"]), 1)


class ValidSignTaskSerializerTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.users = []
        for i in range(3):
            user = UserFactory.create(
                first_name=f"first_name-{i}",
                last_name=f"last_name-{i}",
                email=f"{i}@{i}.nl",
            )
            cls.users.append(user)

        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7",
        )

        cls.zaak = factory(Zaak, zaak)

        Service.objects.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)
        document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
        )
        cls.document_1 = factory(Document, document)
        document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
        )
        cls.document_2 = factory(Document, document)

        cls.zaak_context = ZaakContext(
            zaak=cls.zaak, documents=[cls.document_1, cls.document_2]
        )

        cls.patch_get_zaak_context = patch(
            "zac.camunda.select_documents.serializers.get_zaak_context",
            return_value=cls.zaak_context,
        )

        cls.patch_get_zaak_context_doc_ser = patch(
            "zac.camunda.select_documents.serializers.get_zaak_context",
            return_value=cls.zaak_context,
        )

    def setUp(self):
        super().setUp()

        self.patch_get_zaak_context.start()
        self.addCleanup(self.patch_get_zaak_context.stop)

        self.patch_get_zaak_context_doc_ser.start()
        self.addCleanup(self.patch_get_zaak_context_doc_ser.stop)

    def test_valid_sign_user_serializer(self):
        # Sanity check
        payload = {
            "username": self.users[0].username,
            "email": self.users[0].email,
            "first_name": self.users[0].first_name,
            "last_name": self.users[0].last_name,
        }
        serializer = ValidSignUserSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        self.assertEqual(
            sorted(list(serializer.validated_data.keys())),
            sorted(
                [
                    "username",
                    "email",
                    "first_name",
                    "last_name",
                ]
            ),
        )
        self.assertEqual(
            serializer.validated_data,
            {
                "username": self.users[0].username,
                "email": self.users[0].email,
                "first_name": self.users[0].first_name,
                "last_name": self.users[0].last_name,
            },
        )

    def test_valid_sign_task_serializer(self):
        payload = {
            "assigned_users": [
                {
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                }
                for user in self.users
            ],
            "selected_documents": [self.document_1.url],
        }

        task = _get_task(**{"formKey": "zac:validSign:configurePackage"})
        serializer = ValidSignTaskSerializer(data=payload, context={"task": task})
        serializer.is_valid(raise_exception=True)
        self.assertEqual(
            sorted(list(serializer.validated_data.keys())),
            sorted(
                [
                    "assigned_users",
                    "selected_documents",
                ]
            ),
        )
        self.assertEqual(
            serializer.validated_data["assigned_users"],
            [
                {
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                }
                for user in self.users
            ],
        )

        self.assertEqual(
            serializer.validated_data["selected_documents"], [self.document_1.url]
        )

        variables = serializer.get_process_variables()
        self.assertIn("signers", variables)
        self.assertEqual(
            variables["signers"],
            [
                {
                    "email": user.email,
                    "firstName": user.first_name,
                    "lastName": user.last_name,
                }
                for user in self.users
            ],
        )

    def test_valid_sign_task_serializer_duplicate_users(self):
        payload = {
            "assigned_users": [
                {
                    "username": self.users[0].username,
                    "email": self.users[0].email,
                    "first_name": self.users[0].first_name,
                    "last_name": self.users[0].last_name,
                }
            ]
            * 2,
            "selected_documents": [self.document_1.url],
        }

        task = _get_task(**{"formKey": "zac:validSign:configurePackage"})
        serializer = ValidSignTaskSerializer(data=payload, context={"task": task})
        with self.assertRaises(exceptions.ValidationError) as err:
            serializer.is_valid(raise_exception=True)
        self.assertEqual(
            err.exception.detail["assigned_users"][0].code, "unique-signers"
        )

    def test_valid_sign_task_serializer_empty_users(self):
        payload = {
            "assigned_users": [],
            "selected_documents": [self.document_1.url],
        }

        task = _get_task(**{"formKey": "zac:validSign:configurePackage"})
        serializer = ValidSignTaskSerializer(data=payload, context={"task": task})
        with self.assertRaises(exceptions.ValidationError) as err:
            serializer.is_valid(raise_exception=True)
        self.assertEqual(
            err.exception.detail["assigned_users"][0].code, "empty-signers"
        )

    def test_valid_sign_task_serializer_unknown_signer_missing_all_details(self):
        payload = {
            "assigned_users": [{"username": "some-other-user"}],
            "selected_documents": [self.document_1.url],
        }

        task = _get_task(**{"formKey": "zac:validSign:configurePackage"})
        serializer = ValidSignTaskSerializer(data=payload, context={"task": task})
        with self.assertRaises(exceptions.ValidationError) as err:
            serializer.is_valid(raise_exception=True)
        self.assertEqual(
            err.exception.detail["assigned_users"][0].code, "missing-signer-details"
        )

    def test_valid_sign_task_serializer_unknown_signer_missing_some_details(self):
        payload = {
            "assigned_users": [
                {
                    "username": "some-other-user",
                    "last_name": "last_name",
                    "email": "email@email.com",
                }
            ],
            "selected_documents": [self.document_1.url],
        }

        task = _get_task(**{"formKey": "zac:validSign:configurePackage"})
        serializer = ValidSignTaskSerializer(data=payload, context={"task": task})
        with self.assertRaises(exceptions.ValidationError) as err:
            serializer.is_valid(raise_exception=True)
        self.assertEqual(
            err.exception.detail["assigned_users"][0].code, "missing-signer-details"
        )

    def test_valid_sign_task_serializer_empty_documents(self):
        payload = {
            "assigned_users": [
                {
                    "username": self.users[0].username,
                    "email": self.users[0].email,
                    "first_name": self.users[0].first_name,
                    "last_name": self.users[0].last_name,
                }
            ],
            "selected_documents": [""],
        }

        task = _get_task(**{"formKey": "zac:validSign:configurePackage"})
        serializer = ValidSignTaskSerializer(data=payload, context={"task": task})
        with self.assertRaises(exceptions.ValidationError) as err:
            serializer.is_valid(raise_exception=True)

        self.assertEqual(err.exception.detail["selected_documents"][0][0].code, "blank")
