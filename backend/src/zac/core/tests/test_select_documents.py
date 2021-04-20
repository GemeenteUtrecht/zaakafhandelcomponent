import uuid
from unittest.mock import MagicMock, patch

import requests_mock
from django_camunda.utils import serialize_variable, underscoreize
from rest_framework import exceptions
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import InformatieObjectType, ZaakType
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.api.context import ZaakContext
from zac.camunda.data import ProcessInstance, Task
from zac.camunda.user_tasks import UserTaskData, get_context as _get_context
from zac.contrib.dowc.constants import DocFileTypes
from zac.contrib.dowc.utils import get_dowc_url
from zac.core.models import CoreConfig
from zgw.models.zrc import Zaak

from ..camunda.select_documents.serializers import (
    DocumentSelectContextSerializer,
    DocumentSelectTaskSerializer,
    DocumentSerializer,
)

CATALOGI_ROOT = "http://catalogus.nl/api/v1/"
DOCUMENTS_ROOT = "http://documents.nl/api/v1/"
ZAKEN_ROOT = "http://zaken.nl/api/v1/"
PI_URL = "https://camunda.example.com/engine-rest/process-instance"

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


class GetSelectDocumentContextSerializersTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

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
        cls.document = factory(Document, document)
        catalogus_url = (
            f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        )

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        documenttype = generate_oas_component(
            "ztc",
            "schemas/InformatieObjectType",
            url=f"{CATALOGI_ROOT}informatieobjecttypen/d5d7285d-ce95-4f9e-a36f-181f1c642aa6",
            omschrijving="bijlage",
            catalogus=catalogus_url,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
        )

        cls.document.informatieobjecttype = factory(InformatieObjectType, documenttype)

        cls.zaak_context = ZaakContext(
            zaak=cls.zaak,
            documents=[
                cls.document,
            ],
        )

        cls.patch_get_zaak_context = patch(
            "zac.core.camunda.select_documents.context.get_zaak_context",
            return_value=cls.zaak_context,
        )

        cls.patch_get_zaak_context_serializers = patch(
            "zac.core.camunda.select_documents.serializers.get_zaak_context",
            return_value=cls.zaak_context,
        )

        process_instance_id = uuid.uuid4()
        process_definition_id = uuid.uuid4()
        definition_id = f"BBV_vragen:3:{process_definition_id}"
        cls.process_instance = {
            "id": str(process_instance_id),
            "definition_id": definition_id,
        }

        process_instance = factory(ProcessInstance, cls.process_instance)
        process_instance.get_variable = MagicMock()
        process_instance.get_variable.return_value = None
        cls.patch_get_process_instance = patch(
            "zac.core.camunda.select_documents.context.get_process_instance",
            return_value=process_instance,
        )

        catalogus_url = (
            f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        )
        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            catalogus=catalogus_url,
        )
        cls.zaaktype = factory(ZaakType, zaaktype)

        cls.patch_get_zaaktype = patch(
            "zac.core.camunda.select_documents.context.fetch_zaaktype",
            return_value=cls.zaaktype,
        )

        cls.patch_get_informatieobjecttypen_for_zaaktype = patch(
            "zac.core.camunda.select_documents.context.get_informatieobjecttypen_for_zaaktype",
            return_value=[factory(InformatieObjectType, documenttype)],
        )

    def setUp(self):
        super().setUp()

        self.patch_get_zaak_context.start()
        self.addCleanup(self.patch_get_zaak_context.stop)

        self.patch_get_zaak_context_serializers.start()
        self.addCleanup(self.patch_get_zaak_context_serializers.stop)

        self.patch_get_process_instance.start()
        self.addCleanup(self.patch_get_process_instance.stop)

        self.patch_get_zaaktype.start()
        self.addCleanup(self.patch_get_zaaktype.stop)

        self.patch_get_informatieobjecttypen_for_zaaktype.start()
        self.addCleanup(self.patch_get_informatieobjecttypen_for_zaaktype.stop)

    def test_select_document_serializer(self):
        # Sanity check
        serializer = DocumentSerializer(self.document)
        self.assertEqual(
            serializer.data,
            {
                "beschrijving": self.document.beschrijving,
                "bestandsnaam": self.document.bestandsnaam,
                "bestandsomvang": self.document.bestandsomvang,
                "document_type": self.document.informatieobjecttype.omschrijving,
                "url": self.document.url,
                "read_url": get_dowc_url(self.document, purpose=DocFileTypes.read),
                "versie": self.document.versie,
            },
        )

    def test_select_documents_context_serializer(self):
        task = _get_task(**{"formKey": "zac:documentSelectie"})
        task_data = UserTaskData(task=task, context=_get_context(task))
        serializer = DocumentSelectContextSerializer(instance=task_data)
        self.assertIn("context", serializer.data)
        self.assertIn("documents", serializer.data["context"])
        self.assertEqual(
            serializer.data["context"]["documents"],
            [
                {
                    "beschrijving": self.document.beschrijving,
                    "bestandsnaam": self.document.bestandsnaam,
                    "bestandsomvang": self.document.bestandsomvang,
                    "document_type": self.document.informatieobjecttype.omschrijving,
                    "url": self.document.url,
                    "read_url": get_dowc_url(self.document, purpose=DocFileTypes.read),
                    "versie": self.document.versie,
                }
            ],
        )


@requests_mock.Mocker()
class SelectDocumentsTaskSerializerTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        drc = Service.objects.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)
        config = CoreConfig.get_solo()
        config.primary_drc = drc
        config.save()
        cls.document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
        )
        cls.document_1 = factory(Document, cls.document)
        document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
        )
        cls.document_2 = factory(Document, document)
        catalogus_url = (
            f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        )
        cls.documenttype = generate_oas_component(
            "ztc",
            "schemas/InformatieObjectType",
            url=f"{CATALOGI_ROOT}informatieobjecttypen/d5d7285d-ce95-4f9e-a36f-181f1c642aa6",
            omschrijving="bijlage",
            catalogus=catalogus_url,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
        )
        cls.document_1.informatieobjecttype = factory(
            InformatieObjectType, cls.documenttype
        )
        cls.document_2.informatieobjecttype = factory(
            InformatieObjectType, cls.documenttype
        )
        cls.patch_get_documenten = patch(
            "zac.core.camunda.select_documents.serializers.get_documenten",
            return_value=([cls.document_1, cls.document_2], []),
        )

        process_instance = {
            "id": "c6a5e447-c58e-4986-a30d-54fce7503bbf",
            "definition_id": f"BBV_vragen:3:c6a5e447-ce95-4986-a36f-54fce7503bbf",
        }
        cls.process_instance = factory(ProcessInstance, process_instance)
        cls.patch_get_process_instance = patch(
            "zac.core.camunda.select_documents.serializers.get_process_instance",
            return_value=cls.process_instance,
        )

        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7",
        )
        cls.zaak = factory(Zaak, zaak)
        cls.zaak_context = ZaakContext(
            zaak=cls.zaak, documents=[cls.document_1, cls.document_2]
        )
        cls.patch_get_zaak_context = patch(
            "zac.core.camunda.select_documents.serializers.get_zaak_context",
            return_value=cls.zaak_context,
        )

        catalogus_url = (
            f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        )
        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            informatieobjecttypen=[
                cls.document_1.informatieobjecttype.url,
                cls.document_2.informatieobjecttype.url,
            ],
        )
        cls.zaaktype = factory(ZaakType, zaaktype)
        cls.patch_fetch_zaaktype = patch(
            "zac.core.camunda.select_documents.serializers.fetch_zaaktype",
            return_value=cls.zaaktype,
        )

    def setUp(self):
        super().setUp()

        self.patch_get_documenten.start()
        self.addCleanup(self.patch_get_documenten.stop)

        self.patch_get_process_instance.start()
        self.addCleanup(self.patch_get_process_instance.stop)

        self.patch_get_zaak_context.start()
        self.addCleanup(self.patch_get_zaak_context.stop)

        self.patch_fetch_zaaktype.start()
        self.addCleanup(self.patch_fetch_zaaktype.stop)

    def test_document_select_task_serializer_no_catalogi(self, m):
        payload = {
            "selected_documents": [
                {
                    "document": self.document_1.url,
                    "document_type": self.document_1.informatieobjecttype.omschrijving,
                }
            ]
        }

        task = _get_task(**{"formKey": "zac:documentSelectie"})
        serializer = DocumentSelectTaskSerializer(data=payload, context={"task": task})
        with self.assertRaises(exceptions.ValidationError):
            serializer.is_valid(raise_exception=True)

    @patch(
        "zac.core.camunda.select_documents.serializers.validate_zaak_documents",
        return_value=None,
    )
    def test_document_select_task_serializer(self, m, *mocks):
        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        data = {
            "selected_documents": [
                {
                    "document": self.document_1.url,
                    "document_type": self.document_1.informatieobjecttype.url,
                }
            ]
        }

        task = _get_task(**{"formKey": "zac:documentSelectie"})
        serializer = DocumentSelectTaskSerializer(data=data, context={"task": task})
        m.get(
            f"https://camunda.example.com/engine-rest/process-instance/c6a5e447-c58e-4986-a30d-54fce7503bbf/variables/zaaktype?deserializeValues=false",
            json=serialize_variable(self.zaaktype.url),
        )
        serializer.is_valid(raise_exception=True)

        self.assertIn("selected_documents", serializer.validated_data)
        self.assertEqual(
            serializer.validated_data["selected_documents"],
            [
                {
                    "document": self.document_1.url,
                    "document_type": self.document_1.informatieobjecttype.url,
                }
            ],
        )

    def test_document_select_task_serializer_invalid_document(self, m):
        payload = {
            "selected_documents": [
                {
                    "document": "",
                    "document_type": self.document_1.informatieobjecttype.url,
                }
            ],
        }

        task = _get_task(**{"formKey": "zac:documentSelectie"})
        serializer = DocumentSelectTaskSerializer(data=payload, context={"task": task})
        with self.assertRaises(exceptions.ValidationError) as err:
            serializer.is_valid(raise_exception=True)
        self.assertEqual(
            err.exception.detail["selected_documents"][0]["document"][0].code,
            "blank",
        )

    @patch(
        "zac.core.camunda.select_documents.serializers.validate_zaak_documents",
        return_value=None,
    )
    def test_document_select_task_serializer_on_task_submission(self, m, *mocks):
        mock_service_oas_get(m, DOCUMENTS_ROOT, "drc")
        payload = {
            "selected_documents": [
                {
                    "document": self.document_1.url,
                    "document_type": self.document_1.informatieobjecttype.url,
                }
            ],
        }

        task = _get_task(**{"formKey": "zac:documentSelectie"})
        serializer = DocumentSelectTaskSerializer(data=payload, context={"task": task})
        m.get(
            f"https://camunda.example.com/engine-rest/process-instance/c6a5e447-c58e-4986-a30d-54fce7503bbf/variables/zaaktype?deserializeValues=false",
            json=serialize_variable(self.zaaktype.url),
        )
        m.get(
            f"https://camunda.example.com/engine-rest/process-instance/c6a5e447-c58e-4986-a30d-54fce7503bbf/variables/bronorganisatie?deserializeValues=false",
            json=serialize_variable("123456789"),
        )
        serializer.is_valid(raise_exception=True)

        m.post(
            "http://documents.nl/api/v1/enkelvoudiginformatieobjecten",
            json=[self.document],
            status_code=201,
        )
        serializer.on_task_submission()

        self.assertEqual(m.last_request.method, "POST")
        self.assertEqual(
            m.last_request.url,
            "http://documents.nl/api/v1/enkelvoudiginformatieobjecten",
        )
        self.assertTrue(serializer._documents)

        variables = serializer.get_process_variables()
        self.assertEqual(variables, {"documenten": [self.document["url"]]})
