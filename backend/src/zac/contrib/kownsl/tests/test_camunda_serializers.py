import uuid
from unittest.mock import patch

from django.urls import reverse

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from zds_client.client import ClientError
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import (
    PermissionSetFactory,
    SuperUserFactory,
    UserFactory,
)
from zac.contrib.dowc.constants import DocFileTypes
from zac.contrib.kownsl.api import get_client
from zac.contrib.kownsl.data import Advice, KownslTypes, ReviewRequest
from zac.contrib.kownsl.models import KownslConfig
from zac.core.permissions import zaken_inzien
from zac.core.tests.utils import ClearCachesMixin
from zac.tests.utils import paginated_response
from zgw.models.zrc import Zaak

from ..camunda import (
    AdviceApprovalContext,
    AdviceApprovalContextSerializer,
    AdviceContextSerializer,
    ApprovalContextSerializer,
    ConfigureAdviceRequestSerializer,
    ConfigureApprovalRequestSerializer,
    ConfigureReviewRequest,
    DocumentUserTaskSerializer,
    SelectUsersRevReq,
    SelectUsersRevReqSerializer,
    ZaakInformatieTaskSerializer,
)

DOCUMENTS_ROOT = "http://documents.nl/api/v1/"
ZAKEN_ROOT = "http://zaken.nl/api/v1/"


class CamundaSerializersTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        Service.objects.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        cls.document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
        )

        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
        )

        cls.patch_get_zaak = patch(
            "zac.contrib.kownsl.get_zaak", return_value=factory(Zaak, cls.zaak)
        )
        cls.patch_get_zaak_type = patch(
            "zac.contrib.kownsl.fetch_zaaktype", return_value="some-type"
        )
        cls.patch_get_documents = patch(
            "zac.contrib.kownsl.get_documenten", return_value
        )

    def setUp(self):
        super().setUp()

    def test_document_user_task_serializer(self):
        # Sanity check
        doc = factory(Document, self.document)
        serializer = DocumentUserTaskSerializer(doc)
        self.assertTrue(
            all(
                [
                    field in serializer.data
                    for field in ["beschrijving", "bestandsnaam", "read_url", "url"]
                ]
            )
        )

        self.assertEqual(
            serializer.data["read_url"],
            reverse(
                "dowc:request-doc",
                kwargs={
                    "bronorganisatie": doc.bronorganisatie,
                    "identificatie": doc.identificatie,
                    "purpose": DocFileTypes.read,
                },
            ),
        )

    def test_zaak_informatie_task_serializer(self):
        # Sanity check
        zaak = factory(Zaak, self.zaak)
        serializer = ZaakInformatieTaskSerializer(zaak)
        self.assertTrue(
            all([field in serializer.data for field in ["omschrijving", "toelichting"]])
        )

    def test_advice_approval_context_serializer(self):
        # Sanity check
        zaak = factory(Zaak, self.zaak)
        obj = AdviceApprovalContext(
            review_type="sometype",
            title="some-title",
            zaak_informatie=zaak,
            documents=[factory(Document, self.document)],
        )

        serializer = AdviceApprovalContextSerializer(obj)
        self.assertTrue(
            all(
                [
                    field in serializer.data
                    for field in [
                        "documents",
                        "title",
                        "zaak_informatie",
                    ]
                ]
            )
        )
