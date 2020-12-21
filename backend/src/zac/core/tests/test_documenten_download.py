from django.conf import settings
from django.urls import reverse_lazy

import requests_mock
from django_webtest import WebTest
from rest_framework import status
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import (
    InformatieobjecttypePermissionFactory,
    PermissionSetFactory,
    UserFactory,
)
from zac.core.permissions import zaken_download_documents
from zac.core.tests.utils import ClearCachesMixin
from zac.tests.utils import paginated_response

CATALOGI_ROOT = "https://api.catalogi.nl/api/v1/"
DOCUMENTEN_ROOT = "https://api.documenten.nl/api/v1/"

BRONORGANISATIE = "123456782"
IDENTIFICATIE = "DOC-001"


@requests_mock.Mocker()
class DocumentenDownloadViewTests(ClearCachesMixin, WebTest):
    download_url = reverse_lazy(
        "core:download-document",
        kwargs={
            "bronorganisatie": BRONORGANISATIE,
            "identificatie": IDENTIFICATIE,
        },
    )

    document_1 = {
        "identificatie": IDENTIFICATIE,
        "uuid": "264a9697-fc28-43dc-a431-1b5b8035d40e",
        "url": f"{DOCUMENTEN_ROOT}enkelvoudiginformatieobjecten/264a9697-fc28-43dc-a431-1b5b8035d40e",
        "inhoud": f"{DOCUMENTEN_ROOT}enkelvoudiginformatieobjecten/264a9697-fc28-43dc-a431-1b5b8035d40e/download",
        "titel": "Test Document 1",
        "informatieobjecttype": f"{CATALOGI_ROOT}informatieobjecttypen/c055908a-242b-469d-aead-8b838dc4ac7a",
        "bronorganisatie": BRONORGANISATIE,
        "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
    }

    iot_1 = {
        "url": document_1["informatieobjecttype"],
        "catalogus": f"{CATALOGI_ROOT}catalogussen/1b817d02-09dc-4e5f-9c98-cc9a991b81c6",
        "omschrijving": "Test Omschrijving 1",
        "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
    }

    inhoud_1 = b"Test content 1"

    def setUp(self):
        super().setUp()

        Service.objects.create(api_type=APITypes.drc, api_root=DOCUMENTEN_ROOT)
        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)

        document_data = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
        )
        generate_oas_component(
            "ztc",
            "schemas/InformatieObjectType",
        )

        self.document_1 = {**document_data, **self.document_1}

    def _set_up_mocks(self, m):
        mock_service_oas_get(m, DOCUMENTEN_ROOT, "drc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        m.get(
            f"{DOCUMENTEN_ROOT}enkelvoudiginformatieobjecten?bronorganisatie={BRONORGANISATIE}&identificatie={IDENTIFICATIE}",
            json=paginated_response([self.document_1]),
        )

        m.get(self.document_1["inhoud"], content=self.inhoud_1)

        m.get(self.iot_1["url"], json=self.iot_1)

    def test_login_required(self, m):
        response = self.app.get(self.download_url)
        self.assertRedirects(response, f"{settings.LOGIN_URL}?next={self.download_url}")

    def test_user_auth_no_permissions(self, m):
        self._set_up_mocks(m)

        user = UserFactory.create()
        response = self.app.get(self.download_url, user=user, status=403)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_no_permission_to_catalog(self, m):
        self._set_up_mocks(m)

        user = UserFactory.create()

        # No informatieobjecttype permissions
        permission_set = PermissionSetFactory.create(
            permissions=[zaken_download_documents.name],
            for_user=user,
            catalogus=f"{CATALOGI_ROOT}catalogussen/6f7f6312-8197-417a-b989-7c09f8cd416e",
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={permission_set.catalogus}",
            json={
                "count": 0,
                "next": "",
                "previous": "",
                "results": [],
            },
        )

        response = self.app.get(self.download_url, user=user, status=403)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_permission_to_catalog_and_all_informatieobjecttypes(self, m):
        self._set_up_mocks(m)

        user = UserFactory.create()

        # Permissions to an informatieobjecttype catalogus in the permission and enough confidentiality
        # All informatieobjecttypes allowed as they are not specified
        permission = PermissionSetFactory.create(
            permissions=[zaken_download_documents.name],
            for_user=user,
            catalogus=f"{CATALOGI_ROOT}catalogussen/6f7f6312-8197-417a-b989-7c09f8cd416e",
        )
        InformatieobjecttypePermissionFactory.create(
            catalogus=self.iot_1["catalogus"],
            max_va=VertrouwelijkheidsAanduidingen.geheim,
            permission_set=permission,
        )

        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={permission.catalogus}",
            json={
                "count": 0,
                "next": "",
                "previous": "",
                "results": [],
            },
        )

        response = self.app.get(self.download_url, user=user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content, self.inhoud_1)

    def test_permission_to_catalog_and_iot_but_insufficient_va(self, m):
        self._set_up_mocks(m)

        user = UserFactory.create()

        # Correct catalogus and iot omschrijving specified, but insufficient VA
        permission = PermissionSetFactory.create(
            permissions=[zaken_download_documents.name],
            for_user=user,
            catalogus=f"{CATALOGI_ROOT}catalogussen/6f7f6312-8197-417a-b989-7c09f8cd416e",
        )
        InformatieobjecttypePermissionFactory.create(
            catalogus=self.iot_1["catalogus"],
            omschrijving="Test Omschrijving 1",
            permission_set=permission,
        )

        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={permission.catalogus}",
            json={
                "count": 0,
                "next": "",
                "previous": "",
                "results": [],
            },
        )

        response = self.app.get(self.download_url, user=user, status=403)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_full_permission(self, m):
        self._set_up_mocks(m)

        user = UserFactory.create()

        # All required permissions available
        permission = PermissionSetFactory.create(
            permissions=[zaken_download_documents.name],
            for_user=user,
            catalogus=self.iot_1["catalogus"],
        )
        InformatieobjecttypePermissionFactory.create(
            catalogus=self.iot_1["catalogus"],
            omschrijving="Test Omschrijving 1",
            max_va=VertrouwelijkheidsAanduidingen.geheim,
            permission_set=permission,
        )

        m.get(
            url=f"{CATALOGI_ROOT}zaaktypen?catalogus={self.iot_1['catalogus']}",
            json={
                "count": 0,
                "next": "",
                "previous": "",
                "results": [],
            },
        )

        response = self.app.get(self.download_url, user=user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content, self.inhoud_1)
