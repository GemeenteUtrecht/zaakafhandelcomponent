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
    BlueprintPermissionFactory,
    SuperUserFactory,
    UserFactory,
)
from zac.contrib.dowc.constants import DocFileTypes
from zac.contrib.kownsl.models import KownslConfig
from zac.core.permissions import (
    zaken_download_documents,
    zaken_inzien,
    zaken_update_documents,
    zaken_wijzigen,
)
from zac.core.tests.utils import ClearCachesMixin
from zac.tests.utils import paginated_response
from zgw.models.zrc import Zaak

CATALOGI_ROOT = "http://catalogus.nl/api/v1/"
ZAKEN_ROOT = "http://zaken.nl/api/v1/"
DOCUMENTS_ROOT = "http://documents.nl/api/v1/"
KOWNSL_ROOT = "https://kownsl.nl/"


@requests_mock.Mocker()
class ZaakDocumentsResponseTests(APITestCase):
    """
    Test the API response body for zaak-documents endpoint.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = SuperUserFactory.create()

        catalogus_url = (
            f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        )

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
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
            catalogus=catalogus_url,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="bijlage",
        )

        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            identificatie="ZAAK-2020-0010",
            bronorganisatie="123456782",
            zaaktype=cls.zaaktype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
        )

        Service.objects.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)

        cls.document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            url=f"{DOCUMENTS_ROOT}enkelvoudiginformatieobjecten/0c47fe5e-4fe1-4781-8583-168e0730c9b6",
            identificatie="DOC-2020-007",
            bronorganisatie="123456782",
            informatieobjecttype=cls.documenttype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            auteur="some-auteur",
            beschrijving="some-beschrijving",
            bestandsnaam="some-bestandsnaam",
            locked="True",
            titel="some-titel",
            bestandsomvang="10",
        )
        document = factory(Document, cls.document)
        document.informatieobjecttype = factory(InformatieObjectType, cls.documenttype)
        cls.get_documenten_patcher = patch(
            "zac.core.api.views.get_documenten", return_value=([document], [])
        )

        zaak = factory(Zaak, cls.zaak)
        zaak.zaaktype = factory(ZaakType, cls.zaaktype)
        cls.find_zaak_patcher = patch("zac.core.api.views.find_zaak", return_value=zaak)

        cls.get_review_requests_patcher = patch(
            "zac.core.api.views.get_review_requests", return_value=[]
        )

        cls.get_documenten_permissions_patcher = patch(
            "zac.core.api.permissions.get_documenten", return_value=([document], [])
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

        self.get_documenten_permissions_patcher.start()
        self.addCleanup(self.get_documenten_permissions_patcher.stop)

        # ensure that we have a user with all permissions
        self.client.force_authenticate(user=self.user)

    def test_get_zaak_documents(self, m):
        read_url = reverse(
            "dowc:request-doc",
            kwargs={
                "bronorganisatie": "123456782",
                "identificatie": "DOC-2020-007",
                "purpose": DocFileTypes.read,
            },
        )

        write_url = reverse(
            "dowc:request-doc",
            kwargs={
                "bronorganisatie": "123456782",
                "identificatie": "DOC-2020-007",
                "purpose": DocFileTypes.write,
            },
        )

        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        expected = [
            {
                "url": f"{DOCUMENTS_ROOT}enkelvoudiginformatieobjecten/0c47fe5e-4fe1-4781-8583-168e0730c9b6",
                "auteur": "some-auteur",
                "identificatie": "DOC-2020-007",
                "beschrijving": "some-beschrijving",
                "bestandsnaam": "some-bestandsnaam",
                "locked": True,
                "informatieobjecttype": {
                    "url": f"{CATALOGI_ROOT}informatieobjecttypen/d5d7285d-ce95-4f9e-a36f-181f1c642aa6",
                    "omschrijving": "bijlage",
                },
                "titel": "some-titel",
                "vertrouwelijkheidaanduiding": "Openbaar",
                "bestandsomvang": 10,
                "readUrl": read_url,
                "writeUrl": write_url,
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

    def test_patch_documents(self, m):
        mock_service_oas_get(m, DOCUMENTS_ROOT, "drc")

        document_2 = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            url=f"{DOCUMENTS_ROOT}enkelvoudiginformatieobjecten/0c47fe5e-4fe1-4781-8583-168e0730c9b8",
            informatieobjecttype=self.documenttype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
        )

        payload = [
            {
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduidingen.zeer_geheim,
                "url": self.document["url"],
                "reden": "gewoon zomaar",
            },
            {
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduidingen.geheim,
                "url": document_2["url"],
                "reden": "daarom",
            },
        ]
        m.post(self.document["url"] + "/lock", json={"lock": "a-lock"})
        m.post(document_2["url"] + "/lock", json={"lock": "a-lock"})

        m.patch(
            self.document["url"],
            json={
                **self.document,
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        m.patch(
            document_2["url"],
            json={
                **document_2,
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduidingen.geheim,
            },
        )
        m.post(self.document["url"] + "/unlock", status_code=204)
        m.post(document_2["url"] + "/unlock", status_code=204)

        m.get(
            self.document["url"],
            json={
                **self.document,
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        m.get(
            document_2["url"],
            json={
                **document_2,
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduidingen.geheim,
            },
        )
        documenten = [
            [
                factory(Document, self.document),
                factory(Document, document_2),
            ],
            ["meh", "meh"],
        ]
        drc_client = Service.objects.get(api_root=DOCUMENTS_ROOT).build_client()
        with patch("zac.core.services._client_from_url", return_value=drc_client):
            with patch(
                "zac.core.api.validators.get_documenten",
                return_value=documenten,
            ) as mock_get_documenten:
                with patch(
                    "zac.core.api.permissions.get_documenten", return_value=documenten
                ):
                    response = self.client.patch(self.endpoint, payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check if x audit toelichting is added to headers for audit trail
        relevant_requests = {
            req.url: req.headers for req in m.request_history if req.method == "PATCH"
        }
        self.assertIn(self.document["url"], relevant_requests)
        self.assertIn(document_2["url"], relevant_requests)
        self.assertEqual(
            relevant_requests[self.document["url"]]["X-Audit-Toelichting"],
            "gewoon zomaar",
        )
        self.assertEqual(
            relevant_requests[document_2["url"]]["X-Audit-Toelichting"], "daarom"
        )

        # Make sure get_documenten in validators is only called once and not for every document
        mock_get_documenten.assert_called_once()
        response_data = response.json()
        expected_data = [
            {
                "reden": None,
                "url": "http://documents.nl/api/v1/enkelvoudiginformatieobjecten/0c47fe5e-4fe1-4781-8583-168e0730c9b6",
                "vertrouwelijkheidaanduiding": "zeer_geheim",
                "versie": None,
            },
            {
                "reden": None,
                "url": "http://documents.nl/api/v1/enkelvoudiginformatieobjecten/0c47fe5e-4fe1-4781-8583-168e0730c9b8",
                "vertrouwelijkheidaanduiding": "geheim",
                "versie": None,
            },
        ]
        self.assertEqual(response_data, expected_data)


class ZaakDocumentsPermissionTests(ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        kownsl = Service.objects.create(api_type=APITypes.orc, api_root=KOWNSL_ROOT)

        config = KownslConfig.get_solo()
        config.service = kownsl
        config.save()

        catalogus_url = (
            f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=catalogus_url,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.zeer_geheim,
        )
        cls.documenttype = generate_oas_component(
            "ztc",
            "schemas/InformatieObjectType",
            url=f"{CATALOGI_ROOT}informatieobjecttypen/d5d7285d-ce95-4f9e-a36f-181f1c642aa6",
            catalogus=catalogus_url,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT1",
        )

        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            identificatie="ZAAK-2020-0010",
            bronorganisatie="123456782",
            zaaktype=cls.zaaktype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.zeer_geheim,
        )

        zaak = factory(Zaak, cls.zaak)
        zaak.zaaktype = factory(ZaakType, cls.zaaktype)

        cls.find_zaak_patcher = patch("zac.core.api.views.find_zaak", return_value=zaak)
        cls.get_review_requests_patcher = patch(
            "zac.core.api.views.get_review_requests", return_value=[]
        )

        Service.objects.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)

        cls.document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            url=f"{DOCUMENTS_ROOT}enkelvoudiginformatieobjecten/0c47fe5e-4fe1-4781-8583-168e0730c9b6",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            informatieobjecttype=cls.documenttype["url"],
        )
        cls.doc_obj = factory(Document, cls.document)
        cls.doc_obj.informatieobjecttype = factory(
            InformatieObjectType, cls.documenttype
        )

        cls.endpoint = reverse(
            "zaak-documents",
            kwargs={
                "bronorganisatie": "123456782",
                "identificatie": "ZAAK-2020-0010",
            },
        )

    def _setupMocks(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, KOWNSL_ROOT, "kownsl")
        mock_service_oas_get(m, DOCUMENTS_ROOT, "drc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}",
            json=paginated_response([]),
        )
        m.get(
            f"{KOWNSL_ROOT}api/v1/review-requests?for_zaak={self.zaak['url']}",
            json=[],
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )

    def setUp(self):
        super().setUp()

        self.find_zaak_patcher.start()
        self.addCleanup(self.find_zaak_patcher.stop)

        self.get_review_requests_patcher.start()
        self.addCleanup(self.get_review_requests_patcher.stop)

    def test_not_authenticated(self):
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.patch(self.endpoint, [{}])
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_no_permissions(self):
        user = UserFactory.create()
        self.client.force_authenticate(user=user)

        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.patch(self.endpoint, [{}])
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_has_perm_to_get_but_not_for_zaaktype(self, m):
        self._setupMocks(m)

        user = UserFactory.create()
        BlueprintPermissionFactory.create(
            permission=zaken_inzien.name,
            for_user=user,
            policy={
                "catalogus": "",
                "zaaktype_omschrijving": "",
                "max_va": VertrouwelijkheidsAanduidingen.beperkt_openbaar,
            },
        )
        self.client.force_authenticate(user=user)

        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_has_perm_to_patch_but_not_for_zaaktype(self, m):
        self._setupMocks(m)

        user = UserFactory.create()
        PermissionSetFactory.create(
            permissions=[zaken_wijzigen.name],
            for_user=user,
            catalogus="",
            zaaktype_identificaties=[],
            max_va=VertrouwelijkheidsAanduidingen.beperkt_openbaar,
        )
        self.client.force_authenticate(user=user)

        response = self.client.patch(self.endpoint, [{}])
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_has_perm_to_get_but_not_for_va(self, m):
        self._setupMocks(m)
        user = UserFactory.create()
        # gives them access to the page and zaaktype, but insufficient VA
        BlueprintPermissionFactory.create(
            permission=zaken_inzien.name,
            for_user=user,
            policy={
                "catalogus": self.zaaktype["catalogus"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.openbaar,
            },
        )
        self.client.force_authenticate(user=user)
        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_has_perm_to_patch_but_not_for_va(self, m):
        self._setupMocks(m)

        user = UserFactory.create()
        BlueprintPermissionFactory.create(
            permission=zaken_wijzigen.name,
            for_user=user,
            policy={
                "catalogus": self.zaaktype["catalogus"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.openbaar,
            },
        )
        self.client.force_authenticate(user=user)
        response = self.client.patch(
            self.endpoint,
            [{}],
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_has_perm_to_get_but_not_to_patch(self, m):
        self._setupMocks(m)

        user = UserFactory.create()
        # gives them access to the page, zaaktype and VA specified -> visible
        BlueprintPermissionFactory.create(
            permission=zaken_inzien.name,
            for_user=user,
            policy={
                "catalogus": self.zaaktype["catalogus"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            },
        )
        self.client.force_authenticate(user=user)

        with patch(
            "zac.core.api.views.get_documenten", return_value=([self.doc_obj], [])
        ):
            response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.patch(self.endpoint, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    @patch("zac.core.api.serializers.validate_zaak_documents", return_value=None)
    def test_has_perm_to_to_patch(self, m, *mocks):
        self._setupMocks(m)

        user = UserFactory.create()
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
            permission=zaken_update_documents.name,
            for_user=user,
            policy={
                "catalogus": self.zaaktype["catalogus"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        InformatieobjecttypePermissionFactory.create(
            permission_set=permission_set,
            catalogus=self.zaaktype["catalogus"],
            max_va=VertrouwelijkheidsAanduidingen.zeer_geheim,
        )
        self.client.force_authenticate(user=user)

        with patch(
            "zac.core.api.views.get_documenten", return_value=([self.doc_obj], [])
        ):
            with patch("zac.core.api.views.update_document", return_value=self.doc_obj):
                response = self.client.patch(
                    self.endpoint,
                    [
                        {
                            "reden": "Zomaar",
                            "url": "http://documents.nl/api/v1/enkelvoudiginformatieobjecten/0c47fe5e-4fe1-4781-8583-168e0730c9b8",
                            "vertrouwelijkheidaanduiding": "geheim",
                        }
                    ],
                )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
