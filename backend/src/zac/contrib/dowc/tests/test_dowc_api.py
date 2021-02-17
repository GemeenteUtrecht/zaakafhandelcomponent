import uuid
from unittest.mock import patch

from django.urls import reverse

import jwt
import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import SuperUserFactory
from zac.core.tests.utils import ClearCachesMixin

from ..api import get_client
from ..models import DowcConfig

CATALOGI_ROOT = "http://catalogus.nl/api/v1/"
DOCUMENTS_ROOT = "http://documents.nl/api/v1/"
DOWC_API_ROOT = "https://dowc.nl"

BRONORGANISATIE = "123456782"
IDENTIFICATIE = "DOC-001"


@requests_mock.Mocker()
class DOCAPITests(ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = SuperUserFactory.create()
        Service.objects.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)
        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        cls.service = Service.objects.create(
            label="dowc",
            api_type=APITypes.orc,
            api_root=DOWC_API_ROOT,
            auth_type=AuthTypes.zgw,
            client_id="zac",
            secret="supersecret",
            oas=f"{DOWC_API_ROOT}/api/v1",
            user_id="zac",
        )

        config = DowcConfig.get_solo()
        config.service = cls.service
        config.save()

        cls.catalogus_url = f"{CATALOGI_ROOT}/catalogussen/{uuid.uuid4()}"

        cls.documenttype = generate_oas_component(
            "ztc",
            "schemas/InformatieObjectType",
            url=f"{CATALOGI_ROOT}informatieobjecttypen/{uuid.uuid4()}",
            omschrijving="bijlage",
            catalogus=cls.catalogus_url,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
        )
        cls.document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            url=f"{DOCUMENTS_ROOT}enkelvoudiginformatieobjecten/{uuid.uuid4()}",
            identificatie=BRONORGANISATIE,
            bronorganisatie=IDENTIFICATIE,
            informatieobjecttype=cls.documenttype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            bestandsomvang=10,
        )

        document = factory(Document, cls.document)

        cls.dowc_request = {
            "uuid": str(uuid.uuid4()),
            "magic_url": "webdav-stuff:http://some-url.com/to-a-document/",
            "purpose": "write",
        }

        cls.find_document_patcher = patch(
            "zac.contrib.dowc.views.find_document", return_value=document
        )

        cls.zac_dowc_url = reverse(
            "dowc:request-doc",
            kwargs={
                "bronorganisatie": BRONORGANISATIE,
                "identificatie": IDENTIFICATIE,
                "purpose": cls.dowc_request["purpose"],
            },
        )

    def setUp(self):
        super().setUp()

        self.find_document_patcher.start()
        self.addCleanup(self.find_document_patcher.stop)

    def test_client(self, m):
        mock_service_oas_get(m, self.service.api_root, "dowc", oas_url=self.service.oas)

        client = get_client(user=self.user)
        self.assertIsInstance(client.schema, dict)

        # We're using the ZGW Auth mechanism to pass currently logged-in user information
        self.assertIsNotNone(client.auth)
        self.assertEqual(client.auth.user_id, self.user.username)
        header = client.auth_header["Authorization"]
        self.assertTrue(header.startswith("Bearer "))

        # Inspect the user_id claim
        token = header.split(" ")[1]
        claims = jwt.decode(token, verify=False)
        self.assertEqual(claims["user_id"], self.user.username)

        self.assertEqual(len(m.request_history), 1)
        self.assertEqual(m.last_request.url, f"{self.service.oas}?v=3")

    def test_no_permission(self, m):
        response = self.client.post(self.zac_dowc_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_doc_file_with_all_permissions(self, m):
        mock_service_oas_get(m, self.service.api_root, "dowc", oas_url=self.service.oas)
        self.client.force_authenticate(user=self.user)
        m.post(
            f"{DOWC_API_ROOT}/api/v1/documenten",
            status_code=201,
            json=self.dowc_request,
        )

        with patch(
            "zac.contrib.dowc.views.CanOpenDocuments.has_permission", return_value=True
        ):
            response = self.client.post(self.zac_dowc_url)
            response = response.json()
            self.assertEqual(response["purpose"], self.dowc_request["purpose"])
            self.assertEqual(response["magicUrl"], self.dowc_request["magic_url"])
            self.assertEqual(
                response["deleteUrl"],
                reverse(
                    "dowc:patch-destroy-doc",
                    kwargs={"dowc_uuid": self.dowc_request["uuid"]},
                ),
            )
