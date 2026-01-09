from unittest.mock import patch

from django.urls import reverse_lazy

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

from zac.api.context import ZaakContext
from zac.camunda.data import Task
from zac.camunda.user_tasks import UserTaskData, get_context as _get_context
from zac.core.models import CoreConfig
from zac.tests.compat import generate_oas_component, mock_service_oas_get
from zac.tests.utils import paginated_response
from zgw.models.zrc import Zaak

from ..camunda.select_documents.serializers import (
    DocumentSelectContextSerializer,
    DocumentSelectTaskSerializer,
)
from ..camunda.select_documents.utils import (
    MissingVariable,
    get_zaaktype_from_identificatie,
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
        cls.patch_get_zaak = patch(
            "zac.core.camunda.select_documents.context.get_zaak",
            return_value=cls.zaak,
        )
        cls.patch_get_process_zaak_url = patch(
            "zac.core.camunda.select_documents.context.get_process_zaak_url",
            return_value=cls.zaak.url,
        )

        catalogus_url = (
            f"{CATALOGI_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
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

        catalogus_url = (
            f"{CATALOGI_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        )
        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            catalogus=catalogus_url,
        )
        cls.zaaktype = factory(ZaakType, zaaktype)

        cls.patch_get_zaaktype = patch(
            "zac.core.camunda.select_documents.context.get_zaaktype_from_identificatie",
            return_value=cls.zaaktype,
        )

        cls.patch_get_informatieobjecttypen_for_zaaktype = patch(
            "zac.core.camunda.select_documents.context.get_informatieobjecttypen_for_zaaktype",
            return_value=[factory(InformatieObjectType, documenttype)],
        )

    def setUp(self):
        super().setUp()

        self.patch_get_zaak.start()
        self.addCleanup(self.patch_get_zaak.stop)

        self.patch_get_process_zaak_url.start()
        self.addCleanup(self.patch_get_process_zaak_url.stop)

        self.patch_get_zaaktype.start()
        self.addCleanup(self.patch_get_zaaktype.stop)

        self.patch_get_informatieobjecttypen_for_zaaktype.start()
        self.addCleanup(self.patch_get_informatieobjecttypen_for_zaaktype.stop)

    def test_select_documents_context_serializer(self):
        task = _get_task(**{"formKey": "zac:documentSelectie"})
        task_data = UserTaskData(task=task, context=_get_context(task))
        serializer = DocumentSelectContextSerializer(instance=task_data)
        self.assertIn("context", serializer.data)
        self.assertEqual(
            serializer.data["context"]["documents_link"],
            reverse_lazy(
                "zaak-documents-es",
                kwargs={
                    "bronorganisatie": self.zaak.bronorganisatie,
                    "identificatie": self.zaak.identificatie,
                },
            ),
        )


@requests_mock.Mocker()
class SelectDocumentsTaskSerializerTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        drc = Service.objects.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)
        cls.drc_client = drc.build_client()
        config = CoreConfig.get_solo()
        config.primary_drc = drc
        config.save()
        cls.document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            url=f"{DOCUMENTS_ROOT}d5d7285d-ce95-4f9e-a36f-181f1c642aa6",
            inhoud=f"{DOCUMENTS_ROOT}/d5d7285d-ce95-4f9e-a36f-181f1c642aa6/download",
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

        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7",
        )
        cls.zaak = factory(Zaak, zaak)
        cls.zaak_context = ZaakContext(
            zaak=cls.zaak,
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
        cls.patch_get_zaaktype = patch(
            "zac.core.camunda.select_documents.serializers.get_zaaktype_from_identificatie",
            return_value=cls.zaaktype,
        )

    def setUp(self):
        super().setUp()

        self.patch_get_zaak_context.start()
        self.addCleanup(self.patch_get_zaak_context.stop)

        self.patch_get_zaaktype.start()
        self.addCleanup(self.patch_get_zaaktype.stop)

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

        m.get(self.document_1.url, json=self.document)
        m.get(self.document["inhoud"], content=b"some-content")

        with patch(
            "zac.core.services.client_from_url", return_value=self.drc_client
        ) as mock_drc_client:
            with patch(
                "zac.core.camunda.select_documents.serializers.create_document",
                return_value=self.document_1,
            ) as mock_create_document:
                serializer.on_task_submission()

        mock_drc_client.assert_called_with(self.document_1.url)
        mock_create_document.assert_called_once()

        variables = serializer.get_process_variables()
        self.assertEqual(variables, {"documenten": [self.document["url"]]})


@requests_mock.Mocker()
class GetZaaktypeFromIdentificatieTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        catalogus_url = (
            f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        )
        cls.catalogus = generate_oas_component(
            "ztc",
            "schemas/Catalogus",
            url=catalogus_url,
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            catalogus=catalogus_url,
        )

    def test_get_zaaktype_from_identificatie(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"https://camunda.example.com/engine-rest/task/{TASK_DATA['id']}/variables?deserializeValues=false",
            json={
                "zaaktype": serialize_variable(""),
                "catalogusDomein": serialize_variable("UTRE"),
                "zaaktypeIdentificatie": serialize_variable("53"),
                "catalogusRSIN": serialize_variable("002240022"),
            },
        )
        m.get(
            f"{CATALOGI_ROOT}catalogussen?domein=UTRE&rsin=002240022",
            json=paginated_response([self.catalogus]),
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.catalogus['url']}&identificatie=53",
            json=paginated_response([self.zaaktype]),
        )
        zaaktype = get_zaaktype_from_identificatie(_get_task())
        self.assertEqual(zaaktype.url, self.zaaktype["url"])

    def test_get_zaaktype_from_identificatie_missing_catalogus_domein(self, m):
        m.get(
            f"https://camunda.example.com/engine-rest/task/{TASK_DATA['id']}/variables?deserializeValues=false",
            json={
                "zaaktype": serialize_variable(""),
                "zaaktypeIdentificatie": serialize_variable("53"),
                "catalogusRSIN": serialize_variable("002240022"),
            },
        )
        with self.assertRaises(MissingVariable) as exc:
            get_zaaktype_from_identificatie(_get_task())

        self.assertEqual(
            exc.exception.__str__(), "The variable catalogusDomein is missing or empty."
        )

    def test_get_zaaktype_from_identificatie_missing_zaaktype_identificatie(self, m):
        m.get(
            f"https://camunda.example.com/engine-rest/task/{TASK_DATA['id']}/variables?deserializeValues=false",
            json={
                "zaaktype": serialize_variable(""),
                "catalogusDomein": serialize_variable("UTRE"),
                "catalogusRSIN": serialize_variable("002240022"),
            },
        )
        with self.assertRaises(MissingVariable) as exc:
            get_zaaktype_from_identificatie(_get_task())

        self.assertEqual(
            exc.exception.__str__(),
            "The variable zaaktypeIdentificatie is missing or empty.",
        )

    def test_get_zaaktype_from_identificatie_missing_catalogusRSIN(self, m):
        m.get(
            f"https://camunda.example.com/engine-rest/task/{TASK_DATA['id']}/variables?deserializeValues=false",
            json={
                "zaaktype": serialize_variable(""),
                "catalogusDomein": serialize_variable("UTRE"),
                "zaaktypeIdentificatie": serialize_variable("53"),
            },
        )
        with self.assertRaises(MissingVariable) as exc:
            get_zaaktype_from_identificatie(_get_task())

        self.assertEqual(
            exc.exception.__str__(), "The variable organisatieRSIN is missing or empty."
        )

    def test_get_zaaktype_from_identificatie_use_organisatieRSIN_instead_of_catalogusRSIN(
        self, m
    ):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"https://camunda.example.com/engine-rest/task/{TASK_DATA['id']}/variables?deserializeValues=false",
            json={
                "zaaktype": serialize_variable(""),
                "catalogusDomein": serialize_variable("UTRE"),
                "zaaktypeIdentificatie": serialize_variable("53"),
                "organisatieRSIN": serialize_variable("002240022"),
            },
        )
        m.get(
            f"{CATALOGI_ROOT}catalogussen?domein=UTRE&rsin=002240022",
            json=paginated_response([self.catalogus]),
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.catalogus['url']}&identificatie=53",
            json=paginated_response([self.zaaktype]),
        )
        zaaktype = get_zaaktype_from_identificatie(_get_task())
        self.assertEqual(zaaktype.url, self.zaaktype["url"])

    def test_get_zaaktype_from_identificatie_no_catalogus_found(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"https://camunda.example.com/engine-rest/task/{TASK_DATA['id']}/variables?deserializeValues=false",
            json={
                "zaaktype": serialize_variable(""),
                "catalogusDomein": serialize_variable("UTRE"),
                "zaaktypeIdentificatie": serialize_variable("53"),
                "organisatieRSIN": serialize_variable("002240022"),
            },
        )
        m.get(
            f"{CATALOGI_ROOT}catalogussen?domein=UTRE&rsin=002240022",
            json=paginated_response([]),
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.catalogus['url']}&identificatie=53",
            json=paginated_response([self.zaaktype]),
        )
        with self.assertRaises(ValueError) as exc:
            get_zaaktype_from_identificatie(_get_task())

        self.assertEqual(
            exc.exception.__str__(),
            "No catalogus found with domein UTRE and RSIN 002240022.",
        )

    def test_get_zaaktype_from_identificatie_no_zaaktype_found(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"https://camunda.example.com/engine-rest/task/{TASK_DATA['id']}/variables?deserializeValues=false",
            json={
                "zaaktype": serialize_variable(""),
                "catalogusDomein": serialize_variable("UTRE"),
                "zaaktypeIdentificatie": serialize_variable("53"),
                "organisatieRSIN": serialize_variable("002240022"),
            },
        )
        m.get(
            f"{CATALOGI_ROOT}catalogussen?domein=UTRE&rsin=002240022",
            json=paginated_response([self.catalogus]),
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.catalogus['url']}&identificatie=53",
            json=paginated_response([]),
        )
        with self.assertRaises(ValueError) as exc:
            get_zaaktype_from_identificatie(_get_task())

        self.assertEqual(
            exc.exception.__str__(),
            f"No zaaktype was found with catalogus {self.catalogus['url']} and identificatie 53.",
        )
