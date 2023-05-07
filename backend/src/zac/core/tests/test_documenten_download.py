from unittest import skip

from django.conf import settings
from django.urls import reverse_lazy

import requests_mock
from django_webtest import WebTest
from rest_framework import status
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.constants import PermissionObjectTypeChoices
from zac.accounts.tests.factories import BlueprintPermissionFactory, UserFactory
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
        "beginGeldigheid": "2020-12-01",
        "eindeGeldigheid": None,
        "concept": False,
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

    def test_no_permission_to_iotype(self, m):
        self._set_up_mocks(m)

        user = UserFactory.create()

        BlueprintPermissionFactory.create(
            object_type=PermissionObjectTypeChoices.document,
            role__permissions=[zaken_download_documents.name],
            for_user=user,
            policy={
                "catalogus": self.iot_1["catalogus"],
                "iotype_omschrijving": "",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        response = self.app.get(self.download_url, user=user, status=403)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @skip("Adding one permissions to all iotypen is deprecated")
    def test_permission_to_catalog_and_all_informatieobjecttypes(self, m):
        self._set_up_mocks(m)

        user = UserFactory.create()

        # Permissions to an informatieobjecttype catalogus in the permission and enough confidentiality
        # All informatieobjecttypes allowed as they are not specified

        response = self.app.get(self.download_url, user=user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content, self.inhoud_1)

    def test_permission_to_catalog_and_iot_but_insufficient_va(self, m):
        self._set_up_mocks(m)

        user = UserFactory.create()
        BlueprintPermissionFactory.create(
            object_type=PermissionObjectTypeChoices.document,
            role__permissions=[zaken_download_documents.name],
            for_user=user,
            policy={
                "catalogus": self.iot_1["catalogus"],
                "iotype_omschrijving": "Test Omschrijving 1",
                "max_va": VertrouwelijkheidsAanduidingen.openbaar,
            },
        )

        response = self.app.get(self.download_url, user=user, status=403)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_full_permission(self, m):
        self._set_up_mocks(m)

        user = UserFactory.create()
        BlueprintPermissionFactory.create(
            object_type=PermissionObjectTypeChoices.document,
            role__permissions=[zaken_download_documents.name],
            for_user=user,
            policy={
                "catalogus": self.iot_1["catalogus"],
                "iotype_omschrijving": "Test Omschrijving 1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        response = self.app.get(self.download_url, user=user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content, self.inhoud_1)

    def test_full_permission_blueprint_permission_with_zaak_objecttype(self, m):
        """
        Regression test to make sure BlueprintPermissions with different
        objecttypes than in zac.accounts.backends.MAPPING are ignored/handled
        accordingly.

        """
        self._set_up_mocks(m)

        user = UserFactory.create()
        BlueprintPermissionFactory.create(
            object_type=PermissionObjectTypeChoices.zaak,
            role__permissions=[zaken_download_documents.name],
            for_user=user,
            policy={
                "catalogus": self.iot_1["catalogus"],
                "iotype_omschrijving": "Test Omschrijving 1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        response = self.app.get(self.download_url, user=user, status=403)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        BlueprintPermissionFactory.create(
            object_type=PermissionObjectTypeChoices.document,
            role__permissions=[zaken_download_documents.name],
            for_user=user,
            policy={
                "catalogus": self.iot_1["catalogus"],
                "iotype_omschrijving": "Test Omschrijving 1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        response = self.app.get(self.download_url, user=user)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
