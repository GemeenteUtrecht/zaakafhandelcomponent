from unittest.mock import patch

from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase, APITransactionTestCase
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
from zac.core.permissions import zaken_inzien
from zac.core.tests.utils import ClearCachesMixin
from zac.tests.utils import paginated_response
from zgw.models.zrc import Zaak

CATALOGI_ROOT = "http://catalogus.nl/api/v1/"
ZAKEN_ROOT = "http://zaken.nl/api/v1/"
DOCUMENTS_ROOT = "http://documents.nl/api/v1/"
KOWNSL_ROOT = "https://kownsl.nl/"


@requests_mock.Mocker()
class ZaakDocumentsResponseTests(APITransactionTestCase):
    """
    Test the API response body for zaak-documents endpoint.
    """

    endpoint = reverse(
        "zaak-documents",
        kwargs={
            "bronorganisatie": "123456782",
            "identificatie": "ZAAK-2020-0010",
        },
    )

    def setUp(self):
        super().setUp()
        self.user = SuperUserFactory.create()

    @patch("zac.core.api.views.get_review_requests", return_value=[])
    def test_get_zaak_documents(self, m, *other_mocks):
        self.client.force_authenticate(user=self.user)

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        documenttype = generate_oas_component(
            "ztc",
            "schemas/InformatieObjectType",
            url=f"{CATALOGI_ROOT}informatieobjecttypen/d5d7285d-ce95-4f9e-a36f-181f1c642aa6",
            catalogus=f"{CATALOGI_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="bijlage",
        )

        Service.objects.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)
        document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            url=f"{DOCUMENTS_ROOT}enkelvoudiginformatieobjecten/0c47fe5e-4fe1-4781-8583-168e0730c9b6",
            identificatie="DOC-2020-007",
            bronorganisatie="123456782",
            informatieobjecttype=documenttype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            auteur="some-auteur",
            beschrijving="some-beschrijving",
            bestandsnaam="some-bestandsnaam",
            locked="True",
            titel="some-titel",
            bestandsomvang="10",
        )
        doc_obj = factory(Document, document)
        doc_obj.informatieobjecttype = factory(InformatieObjectType, documenttype)

        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=f"{CATALOGI_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
        )

        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            identificatie="ZAAK-2020-0010",
            bronorganisatie="123456782",
            zaaktype=zaaktype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
        )

        zaak = factory(Zaak, zaak)
        zaak.zaaktype = factory(ZaakType, zaaktype)

        with patch(
            "zac.core.api.views.filter_documenten_for_permissions",
            return_value=[doc_obj],
        ):
            with patch("zac.core.api.views.find_zaak", return_value=zaak):
                with patch(
                    "zac.core.api.views.get_documenten", return_value=([doc_obj], [])
                ):
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
                "readUrl": reverse(
                    "dowc:request-doc",
                    kwargs={
                        "bronorganisatie": "123456782",
                        "identificatie": "DOC-2020-007",
                        "purpose": DocFileTypes.read,
                    },
                ),
                "writeUrl": reverse(
                    "dowc:request-doc",
                    kwargs={
                        "bronorganisatie": "123456782",
                        "identificatie": "DOC-2020-007",
                        "purpose": DocFileTypes.write,
                    },
                ),
            }
        ]
        self.assertEqual(response_data, expected)

    @patch("zac.core.api.views.get_review_requests", return_value=[])
    def test_no_documents(self, m, *other_mocks):
        self.client.force_authenticate(user=self.user)

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=f"{CATALOGI_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
        )

        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            identificatie="ZAAK-2020-0010",
            bronorganisatie="123456782",
            zaaktype=zaaktype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
        )

        zaak = factory(Zaak, zaak)
        zaak.zaaktype = factory(ZaakType, zaaktype)

        with patch("zac.core.api.views.find_zaak", return_value=zaak):
            with patch("zac.core.api.views.get_documenten", return_value=[[], []]):
                with patch(
                    "zac.core.api.views.filter_documenten_for_permissions",
                    return_value=[],
                ):
                    response = self.client.get(self.endpoint)

        self.assertEqual(response.data, [])

    def test_not_found(self, m):
        self.client.force_authenticate(user=self.user)

        with patch("zac.core.api.views.find_zaak", side_effect=ObjectDoesNotExist):
            response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


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
            f"{CATALOGI_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
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
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.beperkt_openbaar,
        )
        zaak = factory(Zaak, cls.zaak)
        zaak.zaaktype = factory(ZaakType, cls.zaaktype)
        cls.find_zaak_patcher = patch("zac.core.api.views.find_zaak", return_value=zaak)

        cls.get_review_requests_patcher = patch(
            "zac.core.api.views.get_review_requests", return_value=[]
        )

        Service.objects.create(api_type=APITypes.drc, api_root=DOCUMENTS_ROOT)

        cls.documenttype = generate_oas_component(
            "ztc",
            "schemas/InformatieObjectType",
            url=f"{CATALOGI_ROOT}informatieobjecttypen/e3f5c6d2-0e49-4293-8428-26139f630950",
            omschrijving="some-iot-omschrijving",
            catalogus=catalogus_url,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.beperkt_openbaar,
        )
        cls.document = generate_oas_component(
            "drc",
            "schemas/EnkelvoudigInformatieObject",
            url=f"{DOCUMENTS_ROOT}enkelvoudiginformatieobjecten/e3f5c6d2-0e49-4293-8428-26139f630951",
            informatieobjecttype=cls.documenttype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.beperkt_openbaar,
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
    def test_has_perm(self, m):
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
