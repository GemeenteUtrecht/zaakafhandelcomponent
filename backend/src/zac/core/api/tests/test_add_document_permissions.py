from io import BytesIO
from unittest.mock import patch

from django.urls import reverse_lazy

import requests_mock
from rest_framework import status
from rest_framework.test import APITransactionTestCase
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.models import APITypes, Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import PermissionDefinitionFactory, UserFactory
from zac.core.tests.utils import ClearCachesMixin

from ...models import CoreConfig
from ...permissions import zaken_add_documents

ZAKEN_ROOT = "https://open-zaak.nl/zaken/api/v1/"
DOCUMENTS_ROOT = "https://open-zaak.nl/documenten/api/v1/"
CATALOGI_ROOT = "https://open-zaak.nl/catalogi/api/v1/"


class AddDocumentPermissionTests(ClearCachesMixin, APITransactionTestCase):
    endpoint = reverse_lazy("add-document")

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

        mock_allowlist = patch("zac.core.rules.test_oo_allowlist", return_value=True)
        mock_allowlist.start()
        self.addCleanup(mock_allowlist.stop)

        self.post_data = {
            "informatieobjecttype": f"{CATALOGI_ROOT}informatieobjecttypen/d1b0512c-cdda-4779-b0bb-7ec1ee516e1b",
            "zaak": f"{ZAKEN_ROOT}zaken/456",
            "file": BytesIO(b"foobar"),
        }

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
        informatieobjecttype = generate_oas_component(
            "ztc",
            "schemas/InformatieObjectType",
            url=f"{CATALOGI_ROOT}informatieobjecttypen/d1b0512c-cdda-4779-b0bb-7ec1ee516e1b",
        )
        ziot = generate_oas_component(
            "ztc",
            "schemas/ZaakTypeInformatieObjectType",
            zaaktype=zaaktype["url"],
            informatieobjecttype=informatieobjecttype["url"],
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
        m.get(informatieobjecttype["url"], json=informatieobjecttype)
        m.get(
            f"{CATALOGI_ROOT}zaaktype-informatieobjecttypen?zaaktype={zaaktype['url']}",
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
        )
        m.get(zaak["url"], json=zaak)

    def test_create_not_logged_in(self):
        response = self.client.post(self.endpoint, self.post_data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_create_logged_in_no_perms(self, m):
        user = UserFactory.create()
        self.client.force_authenticate(user)
        self._setupMocks(m)

        response = self.client.post(self.endpoint, self.post_data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_create_logged_in_with_perms(self, m):
        user = UserFactory.create()
        self.client.force_authenticate(user)
        # set up user permissions
        catalogus = f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        PermissionDefinitionFactory.create(
            object_url="",
            permission=zaken_add_documents.name,
            for_user=user,
            policy={
                "catalogus": catalogus,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        self._setupMocks(m)
        m.post(
            f"{DOCUMENTS_ROOT}enkelvoudiginformatieobjecten",
            json={"url": "https://example.com"},
            status_code=201,
        )
        m.post(
            f"{ZAKEN_ROOT}zaakinformatieobjecten",
            json={"url": "https://example.com"},
            status_code=201,
        )

        response = self.client.post(self.endpoint, self.post_data, format="multipart")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
