from io import BytesIO
from unittest.mock import patch

from django.urls import reverse

import requests_mock
from furl import furl
from rest_framework import status
from rest_framework.test import APITransactionTestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import InformatieObjectType
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.models import APITypes, Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.constants import PermissionObjectType
from zac.accounts.tests.factories import (
    BlueprintPermissionFactory,
    SuperUserFactory,
    UserFactory,
)
from zac.core.tests.utils import ClearCachesMixin

from ...models import CoreConfig
from ...permissions import zaken_add_documents, zaken_update_documents, zaken_wijzigen

ZAKEN_ROOT = "https://open-zaak.nl/zaken/api/v1/"
DOCUMENTS_ROOT = "https://open-zaak.nl/documenten/api/v1/"
CATALOGI_ROOT = "https://open-zaak.nl/catalogi/api/v1/"


class ZaakDocumentPermissionTests(ClearCachesMixin, APITransactionTestCase):
    endpoint = reverse(
        "zaak-document",
        kwargs={
            "bronorganisatie": "123456782",
            "identificatie": "ZAAK-2020-0010",
        },
    )

    def setUp(self):
        super().setUp()

        Service.objects.create(
            label="Zaken API", api_type=APITypes.zrc, api_root=ZAKEN_ROOT
        )
        drc = Service.objects.create(
            label="Documents API", api_type=APITypes.drc, api_root=DOCUMENTS_ROOT
        )
        Service.objects.create(
            label="Catalogi API",
            api_type=APITypes.ztc,
            api_root=CATALOGI_ROOT,
        )

        config = CoreConfig.get_solo()
        config.primary_drc = drc
        config.save()

    def _setupMocks(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, DOCUMENTS_ROOT, "drc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        self.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd",
            omschrijving="ZT1",
        )
        self.informatieobjecttype = generate_oas_component(
            "ztc",
            "schemas/InformatieObjectType",
            url=f"{CATALOGI_ROOT}informatieobjecttypen/d1b0512c-cdda-4779-b0bb-7ec1ee516e1b",
            catalogus=f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd",
            omschrijving="IOT1",
        )
        ziot = generate_oas_component(
            "ztc",
            "schemas/ZaakTypeInformatieObjectType",
            zaaktype=self.zaaktype["url"],
            informatieobjecttype=self.informatieobjecttype["url"],
        )

        m.get(
            f"{CATALOGI_ROOT}zaaktypen",
            json={
                "count": 1,
                "previous": None,
                "next": None,
                "results": [self.zaaktype],
            },
        )
        m.get(self.zaaktype["url"], json=self.zaaktype)
        m.get(self.informatieobjecttype["url"], json=self.informatieobjecttype)
        m.get(
            f"{CATALOGI_ROOT}zaaktype-informatieobjecttypen?zaaktype={self.zaaktype['url']}",
            json={
                "count": 1,
                "next": None,
                "previous": None,
                "results": [ziot],
            },
        )

        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/456",
            zaaktype=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            bronorganisatie="123456782",
            identificatie="ZAAK-2020-0010",
        )
        m.get(zaak["url"], json=zaak)

        patch_find_zaak = patch("zac.core.services.search", return_value=[zaak["url"]])
        patch_find_zaak.start()
        self.addCleanup(patch_find_zaak.stop)

        patch_get_iot = patch(
            "zac.core.api.views.get_informatieobjecttype",
            return_value=factory(InformatieObjectType, self.informatieobjecttype),
        )
        patch_get_iot.start()
        self.addCleanup(patch_get_iot.stop)

    def test_create_not_logged_in(self):
        response = self.client.post(self.endpoint, {}, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_create_logged_in_no_perms(self, m):
        user = UserFactory.create()
        self.client.force_authenticate(user)
        self._setupMocks(m)

        post_data = {
            "informatieobjecttype": f"{CATALOGI_ROOT}informatieobjecttypen/d1b0512c-cdda-4779-b0bb-7ec1ee516e1b",
            "zaak": f"{ZAKEN_ROOT}zaken/456",
            "file": BytesIO(b"foobar"),
        }
        response = self.client.post(self.endpoint, post_data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_create_logged_in_with_perms(self, m):
        user = UserFactory.create()
        self.client.force_authenticate(user)
        self._setupMocks(m)

        # set up user permissions
        catalogus = f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        BlueprintPermissionFactory.create(
            permission=zaken_wijzigen.name,
            for_user=user,
            policy={
                "catalogus": self.zaaktype["catalogus"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        BlueprintPermissionFactory.create(
            permission=zaken_add_documents.name,
            for_user=user,
            policy={
                "catalogus": catalogus,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
        )

        m.post(
            f"{DOCUMENTS_ROOT}enkelvoudiginformatieobjecten",
            json=document,
            status_code=201,
        )

        m.post(
            f"{ZAKEN_ROOT}zaakinformatieobjecten",
            json={"url": "https://example.com"},
            status_code=201,
        )

        post_data = {
            "informatieobjecttype": f"{CATALOGI_ROOT}informatieobjecttypen/d1b0512c-cdda-4779-b0bb-7ec1ee516e1b",
            "zaak": f"{ZAKEN_ROOT}zaken/456",
            "file": BytesIO(b"foobar"),
        }

        response = self.client.post(self.endpoint, post_data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @requests_mock.Mocker()
    def test_has_perm_to_add_document_but_not_edit_documents(self, m):
        user = UserFactory.create()
        self.client.force_authenticate(user=user)
        self._setupMocks(m)

        BlueprintPermissionFactory.create(
            permission=zaken_add_documents.name,
            for_user=user,
            policy={
                "catalogus": self.zaaktype["catalogus"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
        )
        post_data = {
            "reden": "Zomaar",
            "url": document["url"],
            "vertrouwelijkheidaanduiding": "geheim",
            "zaak": f"{ZAKEN_ROOT}zaken/456",
        }

        with patch(
            "zac.core.api.serializers.get_documenten",
            return_value=[[factory(Document, document)], []],
        ):
            response = self.client.patch(self.endpoint, post_data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_has_perm_to_edit_zaak_but_not_to_edit_document(self, m):
        user = UserFactory.create()
        self.client.force_authenticate(user=user)
        self._setupMocks(m)
        BlueprintPermissionFactory.create(
            permission=zaken_wijzigen.name,
            for_user=user,
            policy={
                "catalogus": self.zaaktype["catalogus"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            url=f"{DOCUMENTS_ROOT}123",
            informatieobjecttype=self.informatieobjecttype["url"],
        )
        m.get(document["url"], json=document)
        post_data = {
            "reden": "Zomaar",
            "url": document["url"],
            "vertrouwelijkheidaanduiding": "geheim",
            "zaak": f"{ZAKEN_ROOT}zaken/456",
        }

        with patch(
            "zac.core.api.serializers.get_documenten",
            return_value=[[factory(Document, document)], []],
        ):
            response = self.client.patch(self.endpoint, post_data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_has_perm_to_edit_document_but_not_to_edit_zaak(self, m):
        user = UserFactory.create()
        self.client.force_authenticate(user=user)
        self._setupMocks(m)
        BlueprintPermissionFactory.create(
            object_type=PermissionObjectType.document,
            permission=zaken_update_documents.name,
            for_user=user,
            policy={
                "catalogus": self.informatieobjecttype["catalogus"],
                "iotype_omschrijving": "IOT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            url=f"{DOCUMENTS_ROOT}123",
            informatieobjecttype=self.informatieobjecttype["url"],
        )
        m.get(document["url"], json=document)
        post_data = {
            "reden": "Zomaar",
            "url": document["url"],
            "vertrouwelijkheidaanduiding": "geheim",
            "zaak": f"{ZAKEN_ROOT}zaken/456",
        }

        with patch(
            "zac.core.api.serializers.get_documenten",
            return_value=[[factory(Document, document)], []],
        ):
            response = self.client.patch(self.endpoint, post_data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_has_perm_to_edit_document(self, m):
        user = UserFactory.create()
        self.client.force_authenticate(user=user)
        self._setupMocks(m)
        BlueprintPermissionFactory.create(
            permission=zaken_wijzigen.name,
            for_user=user,
            policy={
                "catalogus": self.zaaktype["catalogus"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        BlueprintPermissionFactory.create(
            object_type=PermissionObjectType.document,
            permission=zaken_update_documents.name,
            for_user=user,
            policy={
                "catalogus": self.informatieobjecttype["catalogus"],
                "iotype_omschrijving": "IOT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            url=f"{DOCUMENTS_ROOT}123",
            informatieobjecttype=self.informatieobjecttype["url"],
        )
        m.get(document["url"], json=document)
        post_data = {
            "reden": "Zomaar",
            "url": document["url"],
            "vertrouwelijkheidaanduiding": "geheim",
            "zaak": f"{ZAKEN_ROOT}zaken/456",
        }

        with patch(
            "zac.core.api.serializers.get_documenten",
            return_value=[[factory(Document, document)], []],
        ):
            with patch(
                "zac.core.api.views.update_document",
                return_value=factory(Document, document),
            ):
                response = self.client.patch(
                    self.endpoint, post_data, format="multipart"
                )

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ZaakDocumentResponseTests(ClearCachesMixin, APITransactionTestCase):
    endpoint = reverse(
        "zaak-document",
        kwargs={
            "bronorganisatie": "123456782",
            "identificatie": "ZAAK-2020-0010",
        },
    )

    def setUp(self):
        super().setUp()

        Service.objects.create(
            label="Zaken API", api_type=APITypes.zrc, api_root=ZAKEN_ROOT
        )
        drc = Service.objects.create(
            label="Documents API", api_type=APITypes.drc, api_root=DOCUMENTS_ROOT
        )
        Service.objects.create(
            label="Catalogi API",
            api_type=APITypes.ztc,
            api_root=CATALOGI_ROOT,
        )

        config = CoreConfig.get_solo()
        config.primary_drc = drc
        config.save()

    def _setupMocks(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, DOCUMENTS_ROOT, "drc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd",
            omschrijving="ZT1",
        )
        self.informatieobjecttype = generate_oas_component(
            "ztc",
            "schemas/InformatieObjectType",
            url=f"{CATALOGI_ROOT}informatieobjecttypen/d1b0512c-cdda-4779-b0bb-7ec1ee516e1b",
        )
        ziot = generate_oas_component(
            "ztc",
            "schemas/ZaakTypeInformatieObjectType",
            zaaktype=zaaktype["url"],
            informatieobjecttype=self.informatieobjecttype["url"],
        )

        m.get(
            f"{CATALOGI_ROOT}zaaktypen",
            json={
                "count": 1,
                "previous": None,
                "next": None,
                "results": [zaaktype],
            },
        )
        m.get(zaaktype["url"], json=zaaktype)
        m.get(self.informatieobjecttype["url"], json=self.informatieobjecttype)

        self.ziot_url = furl(f"{CATALOGI_ROOT}zaaktype-informatieobjecttypen").set(
            {"zaaktype": zaaktype["url"]}
        )
        m.get(
            self.ziot_url.url,
            json={
                "count": 1,
                "next": None,
                "previous": None,
                "results": [ziot],
            },
        )

        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/456",
            zaaktype=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            bronorganisatie="123456782",
            identificatie="ZAAK-2020-0010",
        )
        m.get(zaak["url"], json=zaak)

        patch_find_zaak = patch("zac.core.services.search", return_value=[zaak["url"]])
        patch_find_zaak.start()
        self.addCleanup(patch_find_zaak.stop)

        patch_get_iot = patch(
            "zac.core.api.views.get_informatieobjecttype",
            return_value=factory(InformatieObjectType, self.informatieobjecttype),
        )
        patch_get_iot.start()
        self.addCleanup(patch_get_iot.stop)

    @requests_mock.Mocker()
    def test_add_document(self, m):
        user = SuperUserFactory.create()
        self.client.force_authenticate(user)
        self._setupMocks(m)

        document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            vertrouwelijkheidaanduiding="openbaar",
        )

        m.post(
            f"{DOCUMENTS_ROOT}enkelvoudiginformatieobjecten",
            json=document,
            status_code=201,
        )
        m.post(
            f"{ZAKEN_ROOT}zaakinformatieobjecten",
            json={"url": "https://example.com"},
            status_code=201,
        )

        post_data = {
            "informatieobjecttype": f"{CATALOGI_ROOT}informatieobjecttypen/d1b0512c-cdda-4779-b0bb-7ec1ee516e1b",
            "zaak": f"{ZAKEN_ROOT}zaken/456",
            "file": BytesIO(b"foobar"),
        }

        response = self.client.post(self.endpoint, post_data, format="multipart")

        called_urls = [req.url for req in m.request_history]
        # Check that informatieobjecttype url was called
        self.assertTrue(self.informatieobjecttype["url"] in called_urls)

        # Check that zaakinformatieobjecten url was called
        self.assertTrue(self.ziot_url.url in called_urls)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()
        expected_data = {
            "url": document["url"],
            "auteur": document["auteur"],
            "identificatie": document["identificatie"],
            "beschrijving": document["beschrijving"],
            "bestandsnaam": document["bestandsnaam"],
            "locked": document["locked"],
            "informatieobjecttype": {
                "url": f"{CATALOGI_ROOT}informatieobjecttypen/d1b0512c-cdda-4779-b0bb-7ec1ee516e1b",
                "omschrijving": self.informatieobjecttype["omschrijving"],
            },
            "titel": document["titel"],
            "vertrouwelijkheidaanduiding": "Openbaar",
            "bestandsomvang": document["bestandsomvang"],
            "readUrl": f'/api/dowc/{document["bronorganisatie"]}/{document["identificatie"]}/read',
            "writeUrl": f'/api/dowc/{document["bronorganisatie"]}/{document["identificatie"]}/write',
        }
        self.assertEqual(expected_data, data)

    @requests_mock.Mocker()
    def test_patch_document_no_url_no_reden(self, m):
        user = SuperUserFactory.create()
        self.client.force_authenticate(user)
        self._setupMocks(m)

        post_data = {}

        response = self.client.patch(self.endpoint, post_data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        expected_data = {
            "reden": ["Dit veld is vereist."],
            "url": ["Dit veld is vereist."],
            "zaak": ["Dit veld is vereist."],
        }
        self.assertEqual(data, expected_data)

    @requests_mock.Mocker()
    def test_patch_document_wrong_document(self, m):
        user = SuperUserFactory.create()
        self.client.force_authenticate(user)
        self._setupMocks(m)

        document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            url=f"{DOCUMENTS_ROOT}enkelvoudiginformatieobjecten/0c47fe5e-4fe1-4781-8583-168e0730c9b6",
        )
        post_data = {
            "reden": "gewoon",
            "url": "http://some-other-document.com",
            "zaak": f"{ZAKEN_ROOT}zaken/456",
        }

        with patch(
            "zac.core.api.serializers.get_documenten",
            return_value=[[factory(Document, document)], []],
        ):
            response = self.client.patch(self.endpoint, post_data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        expected_data = {"nonFieldErrors": ["The document is unrelated to the case."]}
        self.assertEqual(data, expected_data)

    @requests_mock.Mocker()
    def test_patch_document(self, m):
        user = SuperUserFactory.create()
        self.client.force_authenticate(user)
        self._setupMocks(m)

        document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            url=f"{DOCUMENTS_ROOT}enkelvoudiginformatieobjecten/0c47fe5e-4fe1-4781-8583-168e0730c9b6",
            informatieobjecttype=self.informatieobjecttype["url"],
            vertrouwelijkheidaanduiding="zaakvertrouwelijk",
            locked=False,
        )
        m.get(document["url"], json=document)

        m.post(
            f"{DOCUMENTS_ROOT}enkelvoudiginformatieobjecten/0c47fe5e-4fe1-4781-8583-168e0730c9b6/lock",
            json={"lock": "slotje"},
        )
        m.post(
            f"{DOCUMENTS_ROOT}enkelvoudiginformatieobjecten/0c47fe5e-4fe1-4781-8583-168e0730c9b6/unlock",
            status_code=204,
            json={},
        )

        m.patch(
            f"{DOCUMENTS_ROOT}enkelvoudiginformatieobjecten/0c47fe5e-4fe1-4781-8583-168e0730c9b6",
            json=document,
        )
        post_data = {
            "reden": "daarom",
            "url": f"{DOCUMENTS_ROOT}enkelvoudiginformatieobjecten/0c47fe5e-4fe1-4781-8583-168e0730c9b6",
            "zaak": f"{ZAKEN_ROOT}zaken/456",
        }
        with patch(
            "zac.core.api.serializers.get_documenten",
            return_value=[[factory(Document, document)], []],
        ):
            response = self.client.patch(self.endpoint, post_data, format="multipart")

        self.maxDiff = None
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        expected_data = {
            "url": "https://open-zaak.nl/documenten/api/v1/enkelvoudiginformatieobjecten/0c47fe5e-4fe1-4781-8583-168e0730c9b6",
            "auteur": document["auteur"],
            "identificatie": document["identificatie"],
            "beschrijving": document["beschrijving"],
            "bestandsnaam": document["bestandsnaam"],
            "locked": False,
            "informatieobjecttype": {
                "url": self.informatieobjecttype["url"],
                "omschrijving": self.informatieobjecttype["omschrijving"],
            },
            "titel": document["titel"],
            "vertrouwelijkheidaanduiding": "Zaakvertrouwelijk",
            "bestandsomvang": None,
            "readUrl": f"/api/dowc/{document['bronorganisatie']}/{document['identificatie']}/read",
            "writeUrl": f"/api/dowc/{document['bronorganisatie']}/{document['identificatie']}/write",
        }
        self.assertEqual(data, expected_data)
