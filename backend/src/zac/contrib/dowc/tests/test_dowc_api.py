import uuid
from unittest.mock import patch

from django.urls import reverse

import jwt
import requests_mock
from furl import furl
from rest_framework import status
from rest_framework.test import APITestCase
from zds_client.auth import JWT_ALG
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.constants import PermissionObjectTypeChoices
from zac.accounts.tests.factories import (
    BlueprintPermissionFactory,
    SuperUserFactory,
    UserFactory,
)
from zac.core.permissions import zaken_download_documents
from zac.core.tests.utils import ClearCachesMixin
from zac.tests.utils import mock_resource_get

from ..api import check_document_status, get_client
from ..constants import DocFileTypes
from ..data import DowcResponse, OpenDowc
from ..models import DowcConfig

CATALOGI_ROOT = "http://catalogus.nl/api/v1/"
CATALOGUS_URL = f"{CATALOGI_ROOT}/catalogussen/{uuid.uuid4()}"
DOCUMENTS_ROOT = "http://documents.nl/api/v1/"
DOWC_API_ROOT = "https://dowc.nl"

BRONORGANISATIE = "123456782"
IDENTIFICATIE = "DOC-001"


@requests_mock.Mocker()
class DOWCAPITests(ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = SuperUserFactory.create()
        Service.objects.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)
        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)

        cls.catalogus = generate_oas_component(
            "ztc",
            "schemas/Catalogus",
            url=CATALOGUS_URL,
            domein="DOME",
        )
        cls.documenttype = generate_oas_component(
            "ztc",
            "schemas/InformatieObjectType",
            url=f"{CATALOGI_ROOT}informatieobjecttypen/{uuid.uuid4()}",
            omschrijving="bijlage",
            catalogus=cls.catalogus["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
        )
        cls.document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            url=f"{DOCUMENTS_ROOT}enkelvoudiginformatieobjecten/{uuid.uuid4()}",
            identificatie=BRONORGANISATIE,
            bronorganisatie=IDENTIFICATIE,
            informatieobjecttype=cls.documenttype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            bestandsomvang=10,
            versie=10,
        )

        document = factory(Document, cls.document)

        cls.uuid = str(uuid.uuid4())
        cls.purpose = DocFileTypes.write
        cls.dowc_response = {
            "drcUrl": furl(document.url).add({"versie": document.versie}).url,
            "purpose": cls.purpose,
            "magicUrl": "webdav-stuff:http://some-url.com/to-a-document/",
            "uuid": cls.uuid,
            "unversionedUrl": document.url,
        }

        cls.find_document_patcher = patch(
            "zac.contrib.dowc.views.find_document", return_value=document
        )
        cls.get_document_patcher = patch(
            "zac.contrib.dowc.views.get_document", return_value=document
        )

        cls.zac_dowc_url = reverse(
            "dowc:request-doc",
            kwargs={
                "bronorganisatie": BRONORGANISATIE,
                "identificatie": IDENTIFICATIE,
                "purpose": cls.purpose,
            },
        )
        cls.delete_dowc_url = reverse(
            "dowc:patch-destroy-doc",
            kwargs={
                "dowc_uuid": cls.uuid,
            },
        )

    def setUp(self):
        super().setUp()

        self.find_document_patcher.start()
        self.addCleanup(self.find_document_patcher.stop)

        self.get_document_patcher.start()
        self.addCleanup(self.get_document_patcher.stop)

        self.service = Service.objects.create(
            label="dowc",
            api_type=APITypes.orc,
            api_root=DOWC_API_ROOT,
            auth_type=AuthTypes.zgw,
            header_key="Authorization",
            header_value="ApplicationToken some-token",
            client_id="zac",
            secret="supersecret",
            oas=f"{DOWC_API_ROOT}/api/v1",
            user_id="zac",
        )

        config = DowcConfig.get_solo()
        config.service = self.service
        config.save()

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
        claims = jwt.decode(
            token, algorithms=[JWT_ALG], options={"verify_signature": False}
        )
        self.assertEqual(claims["user_id"], self.user.username)
        self.assertEqual(claims["email"], self.user.email)
        self.assertEqual(claims["first_name"], self.user.first_name)
        self.assertEqual(claims["last_name"], self.user.last_name)
        self.assertEqual(len(m.request_history), 1)
        self.assertEqual(m.last_request.url, f"{self.service.oas}?v=3")

        # See if application token is used
        client = get_client(force=True)
        self.assertIsNotNone(client.auth_header)
        self.assertEqual(
            client.auth_header, {"Authorization": "ApplicationToken some-token"}
        )

    def test_service_faulty_configuration(self, m):
        self.service.header_value = ""
        self.service.save()
        config = DowcConfig.get_solo()
        config.service = self.service
        config.save()

        with self.assertRaises(AssertionError):
            client = get_client(force=True)

    def test_not_authenticated(self, m):
        response = self.client.post(self.zac_dowc_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_no_permissions(self, m):
        user = UserFactory.create()
        self.client.force_authenticate(user)
        response = self.client.post(self.zac_dowc_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_dowc_file_with_wrong_permissions(self, m):
        mock_service_oas_get(m, self.service.api_root, "dowc", oas_url=self.service.oas)
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.documenttype)
        user = UserFactory.create()
        self.client.force_authenticate(user=user)
        m.post(
            f"{DOWC_API_ROOT}/api/v1/documenten",
            status_code=201,
            json=self.dowc_response,
        )

        BlueprintPermissionFactory.create(
            role__permissions=[zaken_download_documents.name],
            for_user=user,
            policy={
                "catalogus": self.catalogus["domein"],
                "iotype_omschrijving": "some-other-iot",
                "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            },
            object_type=PermissionObjectTypeChoices.document,
        )
        response = self.client.post(
            self.zac_dowc_url,
            HTTP_REFERER="http://www.some-referer-url.com/",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_dowc_file_with_right_permissions_but_wrong_VA(self, m):
        mock_service_oas_get(m, self.service.api_root, "dowc", oas_url=self.service.oas)
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.documenttype)
        user = UserFactory.create()
        self.client.force_authenticate(user=user)
        m.post(
            f"{DOWC_API_ROOT}/api/v1/documenten",
            status_code=201,
            json=self.dowc_response,
        )

        BlueprintPermissionFactory.create(
            role__permissions=[zaken_download_documents.name],
            for_user=user,
            policy={
                "catalogus": self.catalogus["domein"],
                "iotype_omschrijving": self.documenttype["omschrijving"],
                "max_va": VertrouwelijkheidsAanduidingen.openbaar,
            },
            object_type=PermissionObjectTypeChoices.document,
        )
        response = self.client.post(
            self.zac_dowc_url,
            HTTP_REFERER="http://www.some-referer-url.com/",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_dowc_file_with_permissions(self, m):
        mock_service_oas_get(m, self.service.api_root, "dowc", oas_url=self.service.oas)
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.documenttype)
        user = UserFactory.create()
        self.client.force_authenticate(user=user)
        m.post(
            f"{DOWC_API_ROOT}/api/v1/documenten",
            status_code=201,
            json=self.dowc_response,
        )

        BlueprintPermissionFactory.create(
            role__permissions=[zaken_download_documents.name],
            for_user=user,
            policy={
                "catalogus": self.catalogus["domein"],
                "iotype_omschrijving": self.documenttype["omschrijving"],
                "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            },
            object_type=PermissionObjectTypeChoices.document,
        )
        response = self.client.post(
            self.zac_dowc_url,
            {"zaak": "http://some-zaak.nl/"},
            HTTP_REFERER="http://www.some-referer-url.com/",
        )

        self.assertEqual(
            response.json(),
            {
                "drcUrl": self.dowc_response["drcUrl"],
                "purpose": self.dowc_response["purpose"],
                "magicUrl": self.dowc_response["magicUrl"],
                "deleteUrl": reverse(
                    "dowc:patch-destroy-doc",
                    kwargs={"dowc_uuid": self.dowc_response["uuid"]},
                ),
                "unversionedUrl": self.dowc_response["unversionedUrl"],
            },
        )

        self.assertEqual(
            m.last_request.json(),
            {
                "drc_url": self.dowc_response["drcUrl"],
                "purpose": DocFileTypes.write,
                "info_url": "http://www.some-referer-url.com/",
                "zaak": "http://some-zaak.nl/",
            },
        )

    def test_delete_dowc_file_with_permissions(self, m):
        mock_service_oas_get(m, self.service.api_root, "dowc", oas_url=self.service.oas)
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.documenttype)
        user = UserFactory.create()
        self.client.force_authenticate(user=user)
        m.delete(
            f"{DOWC_API_ROOT}/api/v1/documenten/{self.uuid}",
            status_code=201,
            json={"versionedUrl": "something"},
        )

        BlueprintPermissionFactory.create(
            role__permissions=[zaken_download_documents.name],
            for_user=user,
            policy={
                "catalogus": self.catalogus["domein"],
                "iotype_omschrijving": self.documenttype["omschrijving"],
                "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            },
            object_type=PermissionObjectTypeChoices.document,
        )
        with patch("zac.contrib.dowc.views.get_document") as patch_get_document:
            with patch(
                "zac.contrib.dowc.views.invalidate_document_url_cache"
            ) as patch_invalidate_doc_url_cache:
                with patch(
                    "zac.contrib.dowc.views.invalidate_document_other_cache"
                ) as patch_invalidate_doc_other_cache:
                    response = self.client.delete(
                        self.delete_dowc_url,
                    )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            m.last_request.url, f"{DOWC_API_ROOT}/api/v1/documenten/{self.uuid}"
        )
        patch_get_document.assert_called_once()
        patch_invalidate_doc_url_cache.assert_called_once()
        patch_invalidate_doc_other_cache.assert_called_once()

    def test_dowc_file_already_exists_same_user(self, m):
        mock_service_oas_get(m, self.service.api_root, "dowc", oas_url=self.service.oas)
        self.client.force_authenticate(user=self.user)
        m.post(
            f"{DOWC_API_ROOT}/api/v1/documenten",
            status_code=409,
        )
        list_url = furl(f"{DOWC_API_ROOT}/api/v1/documenten")
        list_url.set(
            {
                "drc_url": self.dowc_response["drcUrl"],
                "purpose": DocFileTypes.write,
                "info_url": "http://www.some-referer-url.com/",
            }
        )
        m.get(
            list_url.url,
            status_code=200,
            json=[self.dowc_response],
        )

        with patch(
            "zac.contrib.dowc.views.CanReadDocuments.has_permission", return_value=True
        ):
            response = self.client.post(
                self.zac_dowc_url,
                HTTP_REFERER="http://www.some-referer-url.com/",
            )

        self.assertEqual(response.status_code, 200)

    def test_dowc_file_already_exists_different_user(self, m):
        mock_service_oas_get(m, self.service.api_root, "dowc", oas_url=self.service.oas)
        self.client.force_authenticate(user=self.user)
        m.post(
            f"{DOWC_API_ROOT}/api/v1/documenten",
            status_code=403,
            json={"errors": "this is already locked"},
        )

        with patch(
            "zac.contrib.dowc.views.CanReadDocuments.has_permission", return_value=True
        ):
            response = self.client.post(
                self.zac_dowc_url,
                HTTP_REFERER="http://www.some-referer-url.com/",
            )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["invalidParams"],
            [{"code": "invalid", "name": "errors", "reason": "this is already locked"}],
        )

    def test_check_document_status_documenten(self, m):
        mock_service_oas_get(m, self.service.api_root, "dowc", oas_url=self.service.oas)
        self.client.force_authenticate(user=self.user)
        doc = "https://some-doc.nl/"
        _uuid = uuid.uuid4()
        m.post(
            f"{DOWC_API_ROOT}/api/v1/documenten/status",
            status_code=200,
            json=[
                {"document": doc, "uuid": str(_uuid), "lockedBy": "some-user@zac.nl"}
            ],
        )
        response = check_document_status(documents=[doc])
        self.assertEqual(
            "https://dowc.nl/api/v1/documenten/status",
            m.last_request.url,
        )
        self.assertEqual(
            {"documents": ["https://some-doc.nl/"]},
            m.last_request.json(),
        )
        self.assertEqual(
            response,
            factory(
                OpenDowc,
                [{"document": doc, "uuid": str(_uuid), "lockedBy": "some-user@zac.nl"}],
            ),
        )

    def test_check_document_status_zaak(self, m):
        mock_service_oas_get(m, self.service.api_root, "dowc", oas_url=self.service.oas)
        self.client.force_authenticate(user=self.user)
        doc = "https://some-doc.nl/"
        _uuid = uuid.uuid4()
        m.post(
            f"{DOWC_API_ROOT}/api/v1/documenten/status",
            status_code=200,
            json=[
                {"document": doc, "uuid": str(_uuid), "lockedBy": "some-user@zac.nl"}
            ],
        )
        response = check_document_status(zaak="http://some-zaak.nl/")
        self.assertEqual(
            "https://dowc.nl/api/v1/documenten/status",
            m.last_request.url,
        )
        self.assertEqual(
            {"zaak": "http://some-zaak.nl/"},
            m.last_request.json(),
        )
        self.assertEqual(
            response,
            factory(
                OpenDowc,
                [{"document": doc, "uuid": str(_uuid), "lockedBy": "some-user@zac.nl"}],
            ),
        )
