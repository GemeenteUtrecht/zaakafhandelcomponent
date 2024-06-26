import os
from datetime import date
from io import BytesIO
from os import path
from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.urls import reverse_lazy

import requests_mock
from furl import furl
from rest_framework import status
from rest_framework.test import APITransactionTestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import InformatieObjectType
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.constants import PermissionObjectTypeChoices
from zac.accounts.tests.factories import (
    BlueprintPermissionFactory,
    SuperUserFactory,
    UserFactory,
)
from zac.contrib.dowc.constants import DocFileTypes
from zac.contrib.dowc.data import DowcResponse, OpenDowc
from zac.core.api.data import AuditTrailData
from zac.core.tests.utils import ClearCachesMixin
from zac.tests.utils import mock_resource_get

from ...models import CoreConfig
from ...permissions import (
    zaken_add_documents,
    zaken_geforceerd_bijwerken,
    zaken_update_documents,
    zaken_wijzigen,
)

ZAKEN_ROOT = "https://open-zaak.nl/zaken/api/v1/"
DOCUMENTS_ROOT = "https://open-zaak.nl/documenten/api/v1/"
CATALOGI_ROOT = "https://open-zaak.nl/catalogi/api/v1/"
DOCUMENT_URL = f"{DOCUMENTS_ROOT}enkelvoudiginformatieobjecten/148c998d-85ea-4d4f-b06c-a77c791488f6"
CATALOGUS_URL = f"{CATALOGI_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"


class ZaakDocumentPermissionTests(ClearCachesMixin, APITransactionTestCase):
    endpoint = reverse_lazy("zaak-document")

    catalogus = generate_oas_component(
        "ztc",
        "schemas/Catalogus",
        url=CATALOGUS_URL,
        domein="DOME",
    )
    zaaktype = generate_oas_component(
        "ztc",
        "schemas/ZaakType",
        url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
        identificatie="ZT1",
        catalogus=CATALOGUS_URL,
        omschrijving="ZT1",
    )
    informatieobjecttype = generate_oas_component(
        "ztc",
        "schemas/InformatieObjectType",
        url=f"{CATALOGI_ROOT}informatieobjecttypen/d1b0512c-cdda-4779-b0bb-7ec1ee516e1b",
        catalogus=CATALOGUS_URL,
        omschrijving="IOT1",
    )
    ziot = generate_oas_component(
        "ztc",
        "schemas/ZaakTypeInformatieObjectType",
        zaaktype=zaaktype["url"],
        informatieobjecttype=informatieobjecttype["url"],
    )
    zaak = generate_oas_component(
        "zrc",
        "schemas/Zaak",
        url=f"{ZAKEN_ROOT}zaken/456",
        zaaktype=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
        bronorganisatie="123456782",
        identificatie="ZAAK-2020-0010",
    )
    document = generate_oas_component(
        "drc",
        "schemas/EnkelvoudigInformatieObject",
        url=f"{DOCUMENTS_ROOT}enkelvoudiginformatieobjecten/0c47fe5e-4fe1-4781-8583-168e0730c9b6",
        informatieobjecttype=informatieobjecttype["url"],
    )
    audit_trail = generate_oas_component(
        "drc",
        "schemas/AuditTrail",
        hoofdObject=document["url"],
        resourceUrl=document["url"],
        wijzigingen={
            "oud": {
                "content": "",
                "modified": "2022-03-04T12:11:21.157+01:00",
                "author": "ONBEKEND",
                "versionLabel": "0.2",
            },
            "nieuw": {
                "content": "",
                "modified": "2022-03-04T12:11:39.293+01:00",
                "author": "John Doe",
                "versionLabel": "0.3",
            },
        },
    )
    fn, fext = path.splitext(document["bestandsnaam"])
    patch_get_supported_extensions = patch(
        "zac.contrib.dowc.utils.get_supported_extensions", return_value=[fext]
    )
    patch_update_informatieobject_document = patch(
        "zac.core.api.views.update_informatieobject_document", return_value=None
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

        self.patch_get_supported_extensions.start()
        self.addCleanup(self.patch_get_supported_extensions.stop)
        self.patch_update_informatieobject_document.start()
        self.addCleanup(self.patch_update_informatieobject_document.stop)

    def _setupMocks(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, DOCUMENTS_ROOT, "drc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen",
            json={
                "count": 1,
                "previous": None,
                "next": None,
                "results": [self.zaaktype],
            },
        )
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.zaaktype)
        m.get(self.informatieobjecttype["url"], json=self.informatieobjecttype)
        m.get(
            f"{CATALOGI_ROOT}zaaktype-informatieobjecttypen?zaaktype={self.zaaktype['url']}",
            json={
                "count": 1,
                "next": None,
                "previous": None,
                "results": [self.ziot],
            },
        )
        mock_resource_get(m, self.zaak)
        patch_find_zaak = patch(
            "zac.core.services.search_zaken", return_value=[self.zaak["url"]]
        )
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
        file = BytesIO(b"foobar")
        file.name = "some-file.txt"
        post_data = {
            "informatieobjecttype": f"{CATALOGI_ROOT}informatieobjecttypen/d1b0512c-cdda-4779-b0bb-7ec1ee516e1b",
            "zaak": f"{ZAKEN_ROOT}zaken/456",
            "file": file,
        }

        search_informatieobjects = MagicMock()
        search_informatieobjects.count.return_value = 0
        with patch(
            "zac.core.api.serializers.search_informatieobjects",
            return_value=search_informatieobjects,
        ) as mock_search_informatieobjects:
            response = self.client.post(self.endpoint, post_data, format="multipart")

        mock_search_informatieobjects.assert_called_once()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_create_logged_in_with_perms(self, m, *mocks):
        user = UserFactory.create()
        self.client.force_authenticate(user)
        self._setupMocks(m)

        # set up user permissions
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_wijzigen.name, zaken_add_documents.name],
            for_user=user,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        m.post(
            f"{DOCUMENTS_ROOT}enkelvoudiginformatieobjecten",
            json=self.document,
            status_code=201,
        )

        m.post(
            f"{ZAKEN_ROOT}zaakinformatieobjecten",
            json={"url": "https://example.com"},
            status_code=201,
        )

        file = BytesIO(b"foobar")
        file.name = "some-file.txt"
        post_data = {
            "informatieobjecttype": f"{CATALOGI_ROOT}informatieobjecttypen/d1b0512c-cdda-4779-b0bb-7ec1ee516e1b",
            "zaak": f"{ZAKEN_ROOT}zaken/456",
            "file": file,
        }

        search_informatieobjects = MagicMock()
        search_informatieobjects.count.return_value = 0
        with patch(
            "zac.core.api.views.check_document_status",
            return_value=[],
        ):
            with patch(
                "zac.core.api.serializers.search_informatieobjects",
                return_value=search_informatieobjects,
            ) as mock_search_informatieobjects:
                with patch(
                    "zac.core.api.views.fetch_latest_audit_trail_data_document",
                    return_value=factory(AuditTrailData, self.audit_trail),
                ):
                    response = self.client.post(
                        self.endpoint, post_data, format="multipart"
                    )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mock_search_informatieobjects.assert_called()

    @requests_mock.Mocker()
    def test_has_perm_to_add_document_but_not_edit_documents(self, m):
        user = UserFactory.create()
        self.client.force_authenticate(user=user)
        self._setupMocks(m)

        BlueprintPermissionFactory.create(
            role__permissions=[zaken_add_documents.name],
            for_user=user,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        post_data = {
            "reden": "Zomaar",
            "url": self.document["url"],
            "vertrouwelijkheidaanduiding": "geheim",
            "zaak": f"{ZAKEN_ROOT}zaken/456",
        }

        search_informatieobjects = MagicMock()
        search_informatieobjects.count.return_value = 0
        search_informatieobjects.return_value = [factory(Document, self.document)]
        with patch(
            "zac.core.api.serializers.search_informatieobjects",
            return_value=search_informatieobjects,
        ) as mock_search_informatieobjects:
            response = self.client.patch(self.endpoint, post_data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        mock_search_informatieobjects.assert_called()

    @requests_mock.Mocker()
    def test_has_perm_to_edit_zaak_but_not_to_edit_document(self, m):
        user = UserFactory.create()
        self.client.force_authenticate(user=user)
        self._setupMocks(m)
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_wijzigen.name],
            for_user=user,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        mock_resource_get(m, self.document)
        post_data = {
            "reden": "Zomaar",
            "url": self.document["url"],
            "vertrouwelijkheidaanduiding": "geheim",
            "zaak": f"{ZAKEN_ROOT}zaken/456",
        }

        search_informatieobjects = MagicMock()
        search_informatieobjects.count.return_value = 0
        search_informatieobjects.return_value = [factory(Document, self.document)]
        with patch(
            "zac.core.api.serializers.search_informatieobjects",
            return_value=search_informatieobjects,
        ) as mock_search_informatieobjects:
            response = self.client.patch(self.endpoint, post_data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        mock_search_informatieobjects.assert_called()

    @requests_mock.Mocker()
    def test_has_perm_to_edit_document_but_not_to_edit_zaak(self, m):
        user = UserFactory.create()
        self.client.force_authenticate(user=user)
        self._setupMocks(m)
        BlueprintPermissionFactory.create(
            object_type=PermissionObjectTypeChoices.document,
            role__permissions=[zaken_update_documents.name],
            for_user=user,
            policy={
                "catalogus": self.catalogus["domein"],
                "iotype_omschrijving": "IOT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        mock_resource_get(m, self.document)
        post_data = {
            "reden": "Zomaar",
            "url": self.document["url"],
            "vertrouwelijkheidaanduiding": "geheim",
            "zaak": f"{ZAKEN_ROOT}zaken/456",
        }

        search_informatieobjects = MagicMock()
        search_informatieobjects.count.return_value = 0
        search_informatieobjects.return_value = [factory(Document, self.document)]
        with patch(
            "zac.core.api.serializers.search_informatieobjects",
            return_value=search_informatieobjects,
        ) as mock_search_informatieobjects:
            response = self.client.patch(self.endpoint, post_data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        mock_search_informatieobjects.assert_called()

    @requests_mock.Mocker()
    def test_has_perm_to_edit_document(self, m):
        user = UserFactory.create()
        self.client.force_authenticate(user=user)
        self._setupMocks(m)
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_wijzigen.name],
            for_user=user,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        BlueprintPermissionFactory.create(
            object_type=PermissionObjectTypeChoices.document,
            role__permissions=[zaken_update_documents.name],
            for_user=user,
            policy={
                "catalogus": self.catalogus["domein"],
                "iotype_omschrijving": "IOT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        mock_resource_get(m, self.document)
        post_data = {
            "reden": "Zomaar",
            "url": self.document["url"],
            "vertrouwelijkheidaanduiding": "geheim",
            "zaak": f"{ZAKEN_ROOT}zaken/456",
        }

        search_informatieobjects = MagicMock()
        search_informatieobjects.count.return_value = 0
        search_informatieobjects.return_value = [factory(Document, self.document)]
        with patch(
            "zac.core.api.views.check_document_status",
            return_value=[],
        ):
            with patch(
                "zac.core.api.serializers.search_informatieobjects",
                return_value=search_informatieobjects,
            ) as mock_search_informatieobjects:
                with patch(
                    "zac.core.api.views.update_document",
                    return_value=factory(Document, self.document),
                ):
                    with patch(
                        "zac.core.api.views.fetch_latest_audit_trail_data_document",
                        return_value=factory(AuditTrailData, self.audit_trail),
                    ):
                        response = self.client.patch(
                            self.endpoint, post_data, format="multipart"
                        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_search_informatieobjects.assert_called()

    @requests_mock.Mocker()
    def test_has_perm_to_edit_document_but_zaak_is_closed(self, m):
        user = UserFactory.create()
        self.client.force_authenticate(user=user)
        self._setupMocks(m)
        m.get(self.zaak["url"], json={**self.zaak, "einddatum": "2020-01-01"})
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_wijzigen.name],
            for_user=user,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        BlueprintPermissionFactory.create(
            object_type=PermissionObjectTypeChoices.document,
            role__permissions=[zaken_update_documents.name],
            for_user=user,
            policy={
                "catalogus": self.catalogus["domein"],
                "iotype_omschrijving": "IOT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        mock_resource_get(m, self.document)
        post_data = {
            "reden": "Zomaar",
            "url": self.document["url"],
            "vertrouwelijkheidaanduiding": "geheim",
            "zaak": f"{ZAKEN_ROOT}zaken/456",
        }

        search_informatieobjects = MagicMock()
        search_informatieobjects.count.return_value = 0
        search_informatieobjects.return_value = [factory(Document, self.document)]
        with patch(
            "zac.core.api.serializers.search_informatieobjects",
            return_value=search_informatieobjects,
        ) as mock_search_informatieobjects:
            response = self.client.patch(self.endpoint, post_data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        mock_search_informatieobjects.assert_called()

    @requests_mock.Mocker()
    def test_has_perm_to_edit_document(self, m):
        user = UserFactory.create()
        self.client.force_authenticate(user=user)
        self._setupMocks(m)
        m.get(self.zaak["url"], json={**self.zaak, "einddatum": "2020-01-01"})
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_geforceerd_bijwerken.name],
            for_user=user,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_wijzigen.name],
            for_user=user,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        BlueprintPermissionFactory.create(
            object_type=PermissionObjectTypeChoices.document,
            role__permissions=[zaken_update_documents.name],
            for_user=user,
            policy={
                "catalogus": self.catalogus["domein"],
                "iotype_omschrijving": "IOT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        mock_resource_get(m, self.document)
        post_data = {
            "reden": "Zomaar",
            "url": self.document["url"],
            "vertrouwelijkheidaanduiding": "geheim",
            "zaak": f"{ZAKEN_ROOT}zaken/456",
        }

        search_informatieobjects = MagicMock()
        search_informatieobjects.count.return_value = 0
        search_informatieobjects.return_value = [factory(Document, self.document)]
        with patch(
            "zac.core.api.views.check_document_status",
            return_value=[],
        ):
            with patch(
                "zac.core.api.serializers.search_informatieobjects",
                return_value=search_informatieobjects,
            ) as mock_search_informatieobjects:
                with patch(
                    "zac.core.api.views.update_document",
                    return_value=factory(Document, self.document),
                ):
                    with patch(
                        "zac.core.api.views.fetch_latest_audit_trail_data_document",
                        return_value=factory(AuditTrailData, self.audit_trail),
                    ):
                        response = self.client.patch(
                            self.endpoint, post_data, format="multipart"
                        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mock_search_informatieobjects.assert_called()


@patch.dict(os.environ, {"DEBUG": "False"})
@requests_mock.Mocker()
class ZaakDocumentResponseTests(ClearCachesMixin, APITransactionTestCase):
    endpoint = reverse_lazy("zaak-document")
    zaaktype = generate_oas_component(
        "ztc",
        "schemas/ZaakType",
        url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
        identificatie="ZT1",
        catalogus=f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd",
        omschrijving="ZT1",
    )
    informatieobjecttype = generate_oas_component(
        "ztc",
        "schemas/InformatieObjectType",
        url=f"{CATALOGI_ROOT}informatieobjecttypen/d1b0512c-cdda-4779-b0bb-7ec1ee516e1b",
    )
    informatieobjecttype2 = generate_oas_component(
        "ztc",
        "schemas/InformatieObjectType",
        url=f"{CATALOGI_ROOT}informatieobjecttypen/d1b0512c-cdda-4779-b0bb-7ec1ee516e1c",
    )
    ziot = generate_oas_component(
        "ztc",
        "schemas/ZaakTypeInformatieObjectType",
        zaaktype=zaaktype["url"],
        informatieobjecttype=informatieobjecttype["url"],
        volgnummer=1,
    )
    ziot2 = generate_oas_component(
        "ztc",
        "schemas/ZaakTypeInformatieObjectType",
        zaaktype=zaaktype["url"],
        informatieobjecttype=informatieobjecttype2["url"],
        volgnummer=2,
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
        m.get(
            f"{CATALOGI_ROOT}zaaktypen",
            json={
                "count": 1,
                "previous": None,
                "next": None,
                "results": [self.zaaktype],
            },
        )
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.informatieobjecttype)
        mock_resource_get(m, self.informatieobjecttype2)

        self.ziot_url = furl(f"{CATALOGI_ROOT}zaaktype-informatieobjecttypen").set(
            {"zaaktype": self.zaaktype["url"]}
        )
        m.get(
            self.ziot_url.url,
            json={
                "count": 1,
                "next": None,
                "previous": None,
                "results": [self.ziot, self.ziot2],
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
        mock_resource_get(m, zaak)

        patch_update_informatieobject_document = patch(
            "zac.core.api.views.update_informatieobject_document", return_value=None
        )
        patch_update_informatieobject_document.start()
        self.addCleanup(patch_update_informatieobject_document.stop)
        patch_find_zaak = patch(
            "zac.core.services.search_zaken", return_value=[zaak["url"]]
        )
        patch_find_zaak.start()
        self.addCleanup(patch_find_zaak.stop)

    def test_add_document_with_file(self, m):
        user = SuperUserFactory.create()
        self.client.force_authenticate(user)
        self._setupMocks(m)

        document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            versie=1,
            vertrouwelijkheidaanduiding="openbaar",
            informatieobjecttype=self.informatieobjecttype["url"],
            bestandsnaam="some-bestandsnaam.ext",
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

        file = BytesIO(b"foobar")
        file.name = "some-name.txt"
        post_data = {
            "informatieobjecttype": f"{CATALOGI_ROOT}informatieobjecttypen/d1b0512c-cdda-4779-b0bb-7ec1ee516e1b",
            "zaak": f"{ZAKEN_ROOT}zaken/456",
            "file": file,
        }

        audit_trail = generate_oas_component(
            "drc",
            "schemas/AuditTrail",
            hoofdObject=document["url"],
            resourceUrl=document["url"],
            wijzigingen={
                "oud": {},
                "nieuw": {},
            },
            aanmaakdatum="2022-03-04T12:11:39.293+01:00",
        )
        audit_trail = factory(AuditTrailData, audit_trail)
        fn, fext = path.splitext(document["bestandsnaam"])
        search_informatieobjects = MagicMock()
        search_informatieobjects.count.return_value = 0
        search_informatieobjects.return_value = []
        with patch(
            "zac.core.api.views.check_document_status",
            return_value=[],
        ):
            with patch(
                "zac.core.api.serializers.search_informatieobjects",
                return_value=search_informatieobjects,
            ) as mock_search_informatieobjects:
                with patch(
                    "zac.contrib.dowc.utils.get_supported_extensions",
                    return_value=[fext],
                ):
                    with patch(
                        "zac.core.api.views.fetch_latest_audit_trail_data_document",
                        return_value=audit_trail,
                    ):
                        response = self.client.post(
                            self.endpoint, post_data, format="multipart"
                        )

        mock_search_informatieobjects.assert_called()

        called_urls = [req.url for req in m.request_history]
        # Check that informatieobjecttype url was called
        self.assertTrue(self.informatieobjecttype["url"] in called_urls)

        # Check that zaakinformatieobjecten url was called
        self.assertTrue(self.ziot_url.url in called_urls)

        # Regression test: check that bestandsomvang is now posted too
        for req in m.request_history:
            if (
                req.url == f"{DOCUMENTS_ROOT}enkelvoudiginformatieobjecten"
                and req.method == "POST"
            ):
                self.assertEqual(
                    req.json(),
                    {
                        "bronorganisatie": "123456782",
                        "creatiedatum": date.today().isoformat(),
                        "auteur": user.username,
                        "taal": "nld",
                        "ontvangstdatum": date.today().isoformat(),
                        "bestandsnaam": file.name,
                        "formaat": "text/plain",
                        "inhoud": "Zm9vYmFy",
                        "titel": file.name,
                        "bestandsomvang": 6,
                        "informatieobjecttype": post_data["informatieobjecttype"],
                        "zaak": post_data["zaak"],
                    },
                )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()
        expected_data = {
            "auteur": document["auteur"],
            "beschrijving": document["beschrijving"],
            "bestandsnaam": document["bestandsnaam"],
            "bestandsomvang": document["bestandsomvang"],
            "currentUserIsEditing": False,
            "deleteUrl": "",
            "downloadUrl": reverse_lazy(
                "core:download-document",
                kwargs={
                    "bronorganisatie": document["bronorganisatie"],
                    "identificatie": document["identificatie"],
                },
            )
            + f"?versie={document['versie']}",
            "identificatie": document["identificatie"],
            "informatieobjecttype": {
                "url": f"{CATALOGI_ROOT}informatieobjecttypen/d1b0512c-cdda-4779-b0bb-7ec1ee516e1b",
                "omschrijving": self.informatieobjecttype["omschrijving"],
            },
            "locked": document["locked"],
            "lockedBy": "",
            "readUrl": reverse_lazy(
                "dowc:request-doc",
                kwargs={
                    "bronorganisatie": document["bronorganisatie"],
                    "identificatie": document["identificatie"],
                    "purpose": DocFileTypes.read,
                },
            ),
            "titel": document["titel"],
            "url": document["url"],
            "versie": 1,
            "vertrouwelijkheidaanduiding": "Openbaar",
            "writeUrl": reverse_lazy(
                "dowc:request-doc",
                kwargs={
                    "bronorganisatie": document["bronorganisatie"],
                    "identificatie": document["identificatie"],
                    "purpose": DocFileTypes.write,
                },
            ),
            "lastEditedDate": "2022-03-04T12:11:39.293000+01:00",
        }
        self.assertEqual(expected_data, data)

    def test_add_document_with_file_without_iotype(self, m):
        user = SuperUserFactory.create()
        self.client.force_authenticate(user)
        self._setupMocks(m)

        file = BytesIO(b"foobar")
        file.name = "some-name.txt"
        post_data = {
            "zaak": f"{ZAKEN_ROOT}zaken/456",
            "file": file,
        }

        response = self.client.post(self.endpoint, post_data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "nonFieldErrors",
                    "code": "invalid",
                    "reason": "'informatieobjecttype' is required when 'file' is provided",
                }
            ],
        )

    def test_add_document_with_url(self, m):
        user = SuperUserFactory.create()
        self.client.force_authenticate(user)
        self._setupMocks(m)

        document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            url=DOCUMENT_URL,
            versie=1,
            vertrouwelijkheidaanduiding="openbaar",
            informatieobjecttype=self.informatieobjecttype["url"],
            bestandsnaam="some-bestandsnaam.extension",
        )

        m.get(DOCUMENT_URL, json=document)
        m.post(
            f"{ZAKEN_ROOT}zaakinformatieobjecten",
            json={"url": "https://example.com"},
            status_code=201,
        )

        post_data = {
            "zaak": f"{ZAKEN_ROOT}zaken/456",
            "url": DOCUMENT_URL,
        }

        audit_trail = generate_oas_component(
            "drc",
            "schemas/AuditTrail",
            hoofdObject=document["url"],
            resourceUrl=document["url"],
            wijzigingen={
                "oud": {},
                "nieuw": {},
            },
            aanmaakdatum="2022-03-04T12:11:39.293+01:00",
        )
        audit_trail = factory(AuditTrailData, audit_trail)

        fn, fext = path.splitext(document["bestandsnaam"])
        search_informatieobjects = MagicMock()
        search_informatieobjects.count.return_value = 0
        search_informatieobjects.return_value = []
        with patch(
            "zac.core.api.views.check_document_status",
            return_value=[],
        ):
            with patch(
                "zac.core.api.serializers.search_informatieobjects",
                return_value=search_informatieobjects,
            ) as mock_search_informatieobjects:
                with patch(
                    "zac.contrib.dowc.utils.get_supported_extensions",
                    return_value=[fext],
                ):
                    with patch(
                        "zac.core.api.views.fetch_latest_audit_trail_data_document",
                        return_value=audit_trail,
                    ):
                        response = self.client.post(
                            self.endpoint, post_data, format="multipart"
                        )

        mock_search_informatieobjects.assert_called()
        # Check that zaakinformatieobjecten url was called
        called_urls = [req.url for req in m.request_history]
        self.assertTrue(self.ziot_url.url in called_urls)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        data = response.json()
        expected_data = {
            "auteur": document["auteur"],
            "beschrijving": document["beschrijving"],
            "bestandsnaam": document["bestandsnaam"],
            "bestandsomvang": document["bestandsomvang"],
            "currentUserIsEditing": False,
            "deleteUrl": "",
            "downloadUrl": reverse_lazy(
                "core:download-document",
                kwargs={
                    "bronorganisatie": document["bronorganisatie"],
                    "identificatie": document["identificatie"],
                },
            )
            + f"?versie={document['versie']}",
            "identificatie": document["identificatie"],
            "informatieobjecttype": {
                "url": f"{CATALOGI_ROOT}informatieobjecttypen/d1b0512c-cdda-4779-b0bb-7ec1ee516e1b",
                "omschrijving": self.informatieobjecttype["omschrijving"],
            },
            "locked": document["locked"],
            "lockedBy": "",
            "readUrl": reverse_lazy(
                "dowc:request-doc",
                kwargs={
                    "bronorganisatie": document["bronorganisatie"],
                    "identificatie": document["identificatie"],
                    "purpose": DocFileTypes.read,
                },
            ),
            "titel": document["titel"],
            "url": document["url"],
            "versie": 1,
            "vertrouwelijkheidaanduiding": "Openbaar",
            "writeUrl": reverse_lazy(
                "dowc:request-doc",
                kwargs={
                    "bronorganisatie": document["bronorganisatie"],
                    "identificatie": document["identificatie"],
                    "purpose": DocFileTypes.write,
                },
            ),
            "lastEditedDate": "2022-03-04T12:11:39.293000+01:00",
        }
        self.assertEqual(expected_data, data)

    def test_add_document_with_broken_url(self, m):
        user = SuperUserFactory.create()
        self.client.force_authenticate(user)
        self._setupMocks(m)

        m.get(DOCUMENT_URL, status_code=404)

        post_data = {
            "zaak": f"{ZAKEN_ROOT}zaken/456",
            "url": DOCUMENT_URL,
        }
        response = self.client.post(self.endpoint, post_data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "url",
                    "code": "invalid",
                    "reason": "404 Client Error: None for url: %s" % DOCUMENT_URL,
                }
            ],
        )

    def test_add_document_with_file_and_url(self, m):
        user = SuperUserFactory.create()
        self.client.force_authenticate(user)
        self._setupMocks(m)

        file = BytesIO(b"foobar")
        file.name = "some-name.txt"
        post_data = {
            "informatieobjecttype": self.informatieobjecttype["url"],
            "zaak": f"{ZAKEN_ROOT}zaken/456",
            "file": file,
            "url": DOCUMENT_URL,
        }

        response = self.client.post(self.endpoint, post_data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "nonFieldErrors",
                    "code": "invalid",
                    "reason": "'url' and 'file' are mutually exclusive and can't be provided together.",
                }
            ],
        )

    def test_add_document_no_file_no_url(self, m):
        user = SuperUserFactory.create()
        self.client.force_authenticate(user)
        self._setupMocks(m)

        post_data = {
            "informatieobjecttype": self.informatieobjecttype["url"],
            "zaak": f"{ZAKEN_ROOT}zaken/456",
        }

        response = self.client.post(self.endpoint, post_data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "nonFieldErrors",
                    "code": "invalid",
                    "reason": "Either 'url' or 'file' should be provided.",
                }
            ],
        )

    def test_add_document_with_file_filename_already_exists(self, m):
        user = SuperUserFactory.create()
        self.client.force_authenticate(user)
        self._setupMocks(m)

        document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            versie=1,
            vertrouwelijkheidaanduiding="openbaar",
            bestandsnaam="some-name.txt",
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

        file = BytesIO(b"foobar")
        file.name = "some-name.txt"
        post_data = {
            "informatieobjecttype": f"{CATALOGI_ROOT}informatieobjecttypen/d1b0512c-cdda-4779-b0bb-7ec1ee516e1b",
            "zaak": f"{ZAKEN_ROOT}zaken/456",
            "file": file,
        }
        search_informatieobjects = MagicMock()
        search_informatieobjects.count.return_value = 1
        search_informatieobjects.return_value = []
        with patch(
            "zac.core.api.serializers.search_informatieobjects",
            return_value=search_informatieobjects,
        ) as mock_search_informatieobjects:
            response = self.client.post(self.endpoint, post_data, format="multipart")

        mock_search_informatieobjects.assert_called()
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "nonFieldErrors",
                    "code": "invalid",
                    "reason": "`bestandsnaam`: `some-name.txt` already exists. Please choose a unique `bestandsnaam`.",
                }
            ],
        )

    def test_patch_document_no_url_no_reden(self, m):
        user = SuperUserFactory.create()
        self.client.force_authenticate(user)
        self._setupMocks(m)

        post_data = {}

        response = self.client.patch(self.endpoint, post_data, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {"name": "reden", "code": "required", "reason": "Dit veld is vereist."},
                {"name": "url", "code": "required", "reason": "Dit veld is vereist."},
                {"name": "zaak", "code": "required", "reason": "Dit veld is vereist."},
            ],
        )

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
            "zac.core.api.serializers.search_informatieobjects",
            return_value=[],
        ) as mock_search_informatieobjects:
            response = self.client.patch(self.endpoint, post_data, format="multipart")

        mock_search_informatieobjects.assert_called()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "nonFieldErrors",
                    "code": "invalid",
                    "reason": "Het document is ongerelateerd aan ZAAK-2020-0010.",
                }
            ],
        )

    def test_patch_document_already_locked(self, m):
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
            json={"error": "dit is foute boel"},
            status_code=400,
        )

        post_data = {
            "reden": "daarom",
            "url": f"{DOCUMENTS_ROOT}enkelvoudiginformatieobjecten/0c47fe5e-4fe1-4781-8583-168e0730c9b6",
            "zaak": f"{ZAKEN_ROOT}zaken/456",
        }
        search_informatieobjects = MagicMock()
        search_informatieobjects.count.return_value = 0
        search_informatieobjects.return_value = [factory(Document, document)]
        with patch(
            "zac.core.api.serializers.search_informatieobjects",
            return_value=search_informatieobjects,
        ) as mock_search_informatieobjects:
            response = self.client.patch(self.endpoint, post_data, format="multipart")

        mock_search_informatieobjects.assert_called()
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.json()["detail"], "{'error': 'dit is foute boel'}")

    def test_patch_document(self, m):
        user = SuperUserFactory.create()
        self.client.force_authenticate(user)
        self._setupMocks(m)

        document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            url=f"{DOCUMENTS_ROOT}enkelvoudiginformatieobjecten/0c47fe5e-4fe1-4781-8583-168e0730c9b6",
            informatieobjecttype=self.informatieobjecttype2["url"],
            versie=1,
            vertrouwelijkheidaanduiding="zaakvertrouwelijk",
            locked=False,
            bestandsnaam="some-bestandsnaam.extension",
        )
        mock_resource_get(m, document)

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
            json={
                **document,
                "bestandsnaam": "some-other-bestandsnaam.extension",
                "titel": "some-other-bestandsnaam.extension",
            },
        )
        post_data = {
            "reden": "daarom",
            "url": f"{DOCUMENTS_ROOT}enkelvoudiginformatieobjecten/0c47fe5e-4fe1-4781-8583-168e0730c9b6",
            "zaak": f"{ZAKEN_ROOT}zaken/456",
            "bestandsnaam": "some-other-bestandsnaam.extension",
            "informatieobjecttype": self.informatieobjecttype2["url"],
        }
        audit_trail = generate_oas_component(
            "drc",
            "schemas/AuditTrail",
            hoofdObject=document["url"],
            resourceUrl=document["url"],
            wijzigingen={
                "oud": {
                    "content": "",
                    "modified": "2022-03-04T12:11:21.157+01:00",
                    "author": "ONBEKEND",
                    "versionLabel": "0.2",
                },
                "nieuw": {
                    "content": "",
                    "modified": "2022-03-04T12:11:39.293+01:00",
                    "author": "John Doe",
                    "versionLabel": "0.3",
                },
            },
        )
        audit_trail = factory(AuditTrailData, audit_trail)
        dowc_status = OpenDowc(
            document=document["url"],
            locked_by=user.email,
            uuid=uuid4(),
        )

        fn, fext = path.splitext(document["bestandsnaam"])
        search_informatieobjects = MagicMock()
        search_informatieobjects.count.return_value = 0
        search_informatieobjects.return_value = [factory(Document, document)]
        with patch(
            "zac.core.api.views.check_document_status",
            return_value=[dowc_status],
        ):
            with patch(
                "zac.core.api.serializers.search_informatieobjects",
                return_value=search_informatieobjects,
            ) as mock_search_informatieobjects:
                with patch(
                    "zac.contrib.dowc.utils.get_supported_extensions",
                    return_value=[fext],
                ):
                    with patch(
                        "zac.core.api.views.fetch_latest_audit_trail_data_document",
                        return_value=audit_trail,
                    ):
                        response = self.client.patch(
                            self.endpoint, post_data, format="multipart"
                        )
        mock_search_informatieobjects.assert_called()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        expected_data = {
            "auteur": document["auteur"],
            "beschrijving": document["beschrijving"],
            "bestandsnaam": document["bestandsnaam"],
            "bestandsomvang": None,
            "currentUserIsEditing": True,
            "deleteUrl": reverse_lazy(
                "dowc:patch-destroy-doc", kwargs={"dowc_uuid": dowc_status.uuid}
            ),
            "downloadUrl": reverse_lazy(
                "core:download-document",
                kwargs={
                    "bronorganisatie": document["bronorganisatie"],
                    "identificatie": document["identificatie"],
                },
            )
            + f"?versie={document['versie']}",
            "identificatie": document["identificatie"],
            "informatieobjecttype": {
                "url": self.informatieobjecttype2["url"],
                "omschrijving": self.informatieobjecttype2["omschrijving"],
            },
            "locked": False,
            "lockedBy": "",
            "readUrl": reverse_lazy(
                "dowc:request-doc",
                kwargs={
                    "bronorganisatie": document["bronorganisatie"],
                    "identificatie": document["identificatie"],
                    "purpose": DocFileTypes.read,
                },
            ),
            "titel": document["titel"],
            "url": "https://open-zaak.nl/documenten/api/v1/enkelvoudiginformatieobjecten/0c47fe5e-4fe1-4781-8583-168e0730c9b6",
            "versie": 1,
            "vertrouwelijkheidaanduiding": "Zaakvertrouwelijk",
            "writeUrl": reverse_lazy(
                "dowc:request-doc",
                kwargs={
                    "bronorganisatie": document["bronorganisatie"],
                    "identificatie": document["identificatie"],
                    "purpose": DocFileTypes.write,
                },
            ),
            "lastEditedDate": "2022-03-04T12:11:39.293000+01:00",
        }
        self.assertEqual(data, expected_data)

    def test_patch_document_wrong_iot(self, m):
        user = SuperUserFactory.create()
        self.client.force_authenticate(user)
        self._setupMocks(m)

        document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            url=f"{DOCUMENTS_ROOT}enkelvoudiginformatieobjecten/0c47fe5e-4fe1-4781-8583-168e0730c9b6",
            informatieobjecttype=self.informatieobjecttype["url"],
            versie=1,
            vertrouwelijkheidaanduiding="zaakvertrouwelijk",
            locked=False,
            bestandsnaam="some-bestandsnaam.extension",
        )
        mock_resource_get(m, document)
        post_data = {
            "reden": "daarom",
            "url": f"{DOCUMENTS_ROOT}enkelvoudiginformatieobjecten/0c47fe5e-4fe1-4781-8583-168e0730c9b6",
            "zaak": f"{ZAKEN_ROOT}zaken/456",
            "bestandsnaam": "some-other-bestandsnaam.extension",
            "informatieobjecttype": f"{CATALOGI_ROOT}informatieobjecttypen/d1b0512c-cdda-4779-b0bb-7ec1ee516e1d",
        }
        search_informatieobjects = MagicMock()
        search_informatieobjects.count.return_value = 0
        search_informatieobjects.return_value = [factory(Document, document)]
        with patch(
            "zac.core.api.serializers.search_informatieobjects",
            return_value=search_informatieobjects,
        ) as mock_search_informatieobjects:
            response = self.client.patch(self.endpoint, post_data, format="multipart")

        mock_search_informatieobjects.assert_called()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "nonFieldErrors",
                    "code": "invalid",
                    "reason": "INFORMATIEOBJECTTYPE `https://open-zaak.nl/catalogi/api/v1/informatieobjecttypen/d1b0512c-cdda-4779-b0bb-7ec1ee516e1d` is not related to ZAAKTYPE `ZT1`.",
                }
            ],
        )

    def test_patch_document_filename_already_exists(self, m):
        user = SuperUserFactory.create()
        self.client.force_authenticate(user)
        self._setupMocks(m)

        doc1 = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            url=f"{DOCUMENTS_ROOT}enkelvoudiginformatieobjecten/0c47fe5e-4fe1-4781-8583-168e0730c9b6",
            informatieobjecttype=self.informatieobjecttype["url"],
            versie=1,
            vertrouwelijkheidaanduiding="zaakvertrouwelijk",
            locked=False,
            bestandsnaam="some-bestandsnaam.extension",
        )
        doc2 = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            url=f"{DOCUMENTS_ROOT}enkelvoudiginformatieobjecten/0c47fe5e-4fe1-4781-8583-168e0730c9b5",
            informatieobjecttype=self.informatieobjecttype["url"],
            versie=1,
            vertrouwelijkheidaanduiding="zaakvertrouwelijk",
            locked=False,
            bestandsnaam="some-bestandsnaam-2.extension",
        )

        post_data = {
            "reden": "daarom",
            "url": doc1["url"],
            "zaak": f"{ZAKEN_ROOT}zaken/456",
            "bestandsnaam": doc2["bestandsnaam"],
        }

        search_informatieobjects = MagicMock()
        search_informatieobjects.count.return_value = 1
        search_informatieobjects.return_value = factory(Document, [doc1])
        with patch(
            "zac.core.api.serializers.search_informatieobjects",
            return_value=search_informatieobjects,
        ) as mock_search_informatieobjects:
            response = self.client.patch(self.endpoint, post_data, format="multipart")

        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "nonFieldErrors",
                    "code": "invalid",
                    "reason": "`bestandsnaam`: `some-bestandsnaam-2` already exists. Please choose a unique `bestandsnaam`.",
                }
            ],
        )

    def test_add_document_with_unallowed_file_extension(self, m):
        user = SuperUserFactory.create()
        self.client.force_authenticate(user)
        self._setupMocks(m)

        document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            versie=1,
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

        file = BytesIO(b"foobar")
        file.name = "some-unallowed-extension.ext"
        post_data = {
            "informatieobjecttype": f"{CATALOGI_ROOT}informatieobjecttypen/d1b0512c-cdda-4779-b0bb-7ec1ee516e1b",
            "zaak": f"{ZAKEN_ROOT}zaken/456",
            "file": file,
        }

        audit_trail = generate_oas_component(
            "drc",
            "schemas/AuditTrail",
            hoofdObject=document["url"],
            resourceUrl=document["url"],
            wijzigingen={
                "oud": {},
                "nieuw": {},
            },
            aanmaakdatum="2022-03-04T12:11:39.293+01:00",
        )
        audit_trail = factory(AuditTrailData, audit_trail)

        with patch(
            "zac.core.api.views.check_document_status",
            return_value=[],
        ):
            with patch(
                "zac.core.api.views.fetch_latest_audit_trail_data_document",
                return_value=audit_trail,
            ):
                response = self.client.post(
                    self.endpoint, post_data, format="multipart"
                )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "file",
                    "code": "invalid",
                    "reason": "File format not allowed. Please use one of the following file formats: CSV, DOC, DOCX, EML, JPEG, MBOX, MSG, ODP, ODS, ODT, PDF, PNG, PPT, PPTX, TXT, TIFF, XLS, XLSX.",
                }
            ],
        )

    def test_add_document_with_unallowed_filename(self, m):
        user = SuperUserFactory.create()
        self.client.force_authenticate(user)
        self._setupMocks(m)

        document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            versie=1,
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

        file = BytesIO(b"foobar")
        file.name = "some.illegal.file.name"
        post_data = {
            "informatieobjecttype": f"{CATALOGI_ROOT}informatieobjecttypen/d1b0512c-cdda-4779-b0bb-7ec1ee516e1b",
            "zaak": f"{ZAKEN_ROOT}zaken/456",
            "file": file,
        }

        audit_trail = generate_oas_component(
            "drc",
            "schemas/AuditTrail",
            hoofdObject=document["url"],
            resourceUrl=document["url"],
            wijzigingen={
                "oud": {},
                "nieuw": {},
            },
            aanmaakdatum="2022-03-04T12:11:39.293+01:00",
        )
        audit_trail = factory(AuditTrailData, audit_trail)

        with patch(
            "zac.core.api.views.check_document_status",
            return_value=[],
        ):
            with patch(
                "zac.core.api.views.fetch_latest_audit_trail_data_document",
                return_value=audit_trail,
            ):
                response = self.client.post(
                    self.endpoint, post_data, format="multipart"
                )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "file",
                    "code": "invalid",
                    "reason": "Only alphanumerical characters, whitespaces, -_() and 1 file extension are allowed.",
                }
            ],
        )
