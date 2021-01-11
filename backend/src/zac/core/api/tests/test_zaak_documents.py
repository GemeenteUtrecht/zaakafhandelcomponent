from unittest.mock import patch

from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import InformatieObjectType, ZaakType
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.api_models.documenten import Document
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import (
    PermissionSetFactory,
    SuperUserFactory,
    UserFactory,
)
from zac.core.permissions import zaken_inzien
from zac.core.tests.utils import ClearCachesMixin
from zac.tests.utils import paginated_response
from zgw.models.zrc import Zaak

CATALOGI_ROOT = "http://catalogus.nl/api/v1/"
ZAKEN_ROOT = "http://zaken.nl/api/v1/"
DOCUMENTS_ROOT = "http://documents.nl/api/v1/"


@requests_mock.Mocker()
class ZaakDocumentsResponseTests(APITestCase):
    """
    Test the API response body for zaak-documents endpoint.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = SuperUserFactory.create()

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        Service.objects.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)

        catalogus_url = (
            f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=catalogus_url,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
        )
        cls.documenttype = generate_oas_component(
            "ztc",
            "schemas/InformatieObjectType",
            url=f"{CATALOGI_ROOT}informatieobjecttypen/d5d7285d-ce95-4f9e-a36f-181f1c642aa6",
            omschrijving="bijlage",
            catalogus=catalogus_url,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
        )
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            identificatie="ZAAK-2020-0010",
            bronorganisatie="123456782",
            zaaktype=cls.zaaktype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            startdatum="2020-12-25",
            uiterlijkeEinddatumAfdoening="2021-01-04",
        )
        cls.document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            url=f"{DOCUMENTS_ROOT}enkelvoudiginformatieobjecten/0c47fe5e-4fe1-4781-8583-168e0730c9b6",
            identificatie="DOC-2020-007",
            bronorganisatie="123456782",
            informatieobjecttype=cls.documenttype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            bestandsomvang=10,
        )

        zaak = factory(Zaak, cls.zaak)
        zaak.zaaktype = factory(ZaakType, cls.zaaktype)

        document = factory(Document, cls.document)
        document.informatieobjecttype = factory(InformatieObjectType, cls.documenttype)

        cls.find_zaak_patcher = patch("zac.core.api.views.find_zaak", return_value=zaak)
        cls.get_review_requests_patcher = patch(
            "zac.core.api.views.get_review_requests", return_value=[]
        )
        cls.get_documenten_patcher = patch(
            "zac.core.api.views.get_documenten", return_value=([document], [])
        )

        cls.endpoint = reverse(
            "zaak-documents",
            kwargs={
                "bronorganisatie": "123456782",
                "identificatie": "ZAAK-2020-0010",
            },
        )

    def setUp(self):
        super().setUp()

        self.find_zaak_patcher.start()
        self.addCleanup(self.find_zaak_patcher.stop)

        self.get_review_requests_patcher.start()
        self.addCleanup(self.get_review_requests_patcher.stop)

        self.get_documenten_patcher.start()
        self.addCleanup(self.get_documenten_patcher.stop)

        # ensure that we have a user with all permissions
        self.client.force_authenticate(user=self.user)

    def test_get_zaak_documents(self, m):
        download_url = reverse(
            "core:download-document",
            kwargs={
                "bronorganisatie": "123456782",
                "identificatie": "DOC-2020-007",
            },
        )

        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        expected = [
            {
                "url": self.document["url"],
                "auteur": self.document["auteur"],
                "identificatie": "DOC-2020-007",
                "beschrijving": self.document["beschrijving"],
                "bestandsnaam": self.document["bestandsnaam"],
                "locked": self.document["locked"],
                "informatieobjecttype": {
                    "url": f"{CATALOGI_ROOT}informatieobjecttypen/d5d7285d-ce95-4f9e-a36f-181f1c642aa6",
                    "omschrijving": "bijlage",
                },
                "titel": self.document["titel"],
                "vertrouwelijkheidaanduiding": "Openbaar",
                "bestandsomvang": 10,
                "downloadUrl": f"http://testserver{download_url}",
            }
        ]
        self.assertEqual(response_data, expected)

    def test_no_documents(self, m):
        with patch("zac.core.api.views.get_documenten", return_value=[[], []]):
            response = self.client.get(self.endpoint)

        self.assertEqual(response.data, [])

    def test_not_found(self, m):
        with patch("zac.core.api.views.find_zaak", side_effect=ObjectDoesNotExist):
            response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class ZaakDocumentsPermissionTests(ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)

        catalogus_url = (
            f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=catalogus_url,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
        )
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            identificatie="ZAAK-2020-0010",
            bronorganisatie="123456782",
            zaaktype=cls.zaaktype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.beperkt_openbaar,
            startdatum="2020-12-25",
            uiterlijkeEinddatumAfdoening="2021-01-04",
        )

        zaak = factory(Zaak, cls.zaak)
        zaak.zaaktype = factory(ZaakType, cls.zaaktype)

        cls.find_zaak_patcher = patch("zac.core.api.views.find_zaak", return_value=zaak)
        cls.get_review_requests_patcher = patch(
            "zac.core.api.views.get_review_requests", return_value=[]
        )
        cls.get_documenten_patcher = patch(
            "zac.core.api.views.get_documenten", return_value=([], [])
        )

        cls.endpoint = reverse(
            "zaak-documents",
            kwargs={
                "bronorganisatie": "123456782",
                "identificatie": "ZAAK-2020-0010",
            },
        )

    def setUp(self):
        super().setUp()

        self.find_zaak_patcher.start()
        self.addCleanup(self.find_zaak_patcher.stop)

        self.get_review_requests_patcher.start()
        self.addCleanup(self.get_review_requests_patcher.stop)

        self.get_documenten_patcher.start()
        self.addCleanup(self.get_documenten_patcher.stop)

    def test_not_authenticated(self):
        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_no_permissions(self):
        user = UserFactory.create()
        self.client.force_authenticate(user=user)

        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_has_perm_but_not_for_zaaktype(self):
        # gives them access to the page, but no catalogus specified -> nothing visible
        user = UserFactory.create()
        PermissionSetFactory.create(
            permissions=[zaken_inzien.name],
            for_user=user,
            catalogus="",
            zaaktype_identificaties=[],
            max_va=VertrouwelijkheidsAanduidingen.beperkt_openbaar,
        )
        self.client.force_authenticate(user=user)

        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_has_perm_but_not_for_va(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        user = UserFactory.create()
        # gives them access to the page and zaaktype, but insufficient VA
        PermissionSetFactory.create(
            permissions=[zaken_inzien.name],
            for_user=user,
            catalogus=self.zaaktype["catalogus"],
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.openbaar,
        )
        self.client.force_authenticate(user=user)

        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_has_perm(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        user = UserFactory.create()
        # gives them access to the page, zaaktype and VA specified -> visible
        PermissionSetFactory.create(
            permissions=[zaken_inzien.name],
            for_user=user,
            catalogus=self.zaaktype["catalogus"],
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
        )
        self.client.force_authenticate(user=user)

        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
