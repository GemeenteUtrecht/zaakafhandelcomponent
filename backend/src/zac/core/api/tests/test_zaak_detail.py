from unittest.mock import patch

from django.core.cache import cache
from django.urls import reverse

import requests_mock
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ResultaatType, ZaakType
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.api_models.zaken import Resultaat
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import (
    AccessRequestFactory,
    AtomicPermissionFactory,
    BlueprintPermissionFactory,
    SuperUserFactory,
    UserFactory,
)
from zac.contrib.kownsl.models import KownslConfig
from zac.core.permissions import zaken_inzien, zaken_request_access, zaken_wijzigen
from zac.core.tests.utils import ClearCachesMixin
from zac.elasticsearch.tests.utils import ESMixin
from zac.tests.utils import mock_resource_get, paginated_response
from zgw.models.zrc import Zaak

CATALOGI_ROOT = "http://catalogus.nl/api/v1/"
ZAKEN_ROOT = "http://zaken.nl/api/v1/"
KOWNSL_ROOT = "https://kownsl.nl/"


@requests_mock.Mocker()
class ZaakDetailResponseTests(ESMixin, ClearCachesMixin, APITestCase):
    """
    Test the API response body for zaak-detail endpoint.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = SuperUserFactory.create()

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
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            startdatum="2020-12-25",
            uiterlijkeEinddatumAfdoening="2021-01-04",
        )

        resultaattype = generate_oas_component(
            "ztc",
            "schemas/ResultaatType",
            url=f"{CATALOGI_ROOT}resultaattypen/362b23eb-d8a9-486f-b236-8adb58ebc18f",
            zaaktype=cls.zaaktype["url"],
            omschrijving="geannuleerd",
        )
        cls.resultaat = generate_oas_component(
            "zrc",
            "schemas/Resultaat",
            url=f"{ZAKEN_ROOT}resultaten/c8ebd02f-3265-4f2c-a7d7-f773ad7f589d",
            zaak=cls.zaak["url"],
            resultaattype=resultaattype["url"],
        )

        resultaat = factory(Resultaat, cls.resultaat)
        resultaat.resultaattype = factory(ResultaatType, resultaattype)
        cls.resultaat = {
            "url": cls.resultaat["url"],
            "resultaattype": {
                "url": resultaattype["url"],
                "omschrijving": resultaattype["omschrijving"],
            },
            "toelichting": cls.resultaat["toelichting"],
        }

        cls.patch_get_resultaat = patch(
            "zac.core.api.views.get_resultaat", return_value=resultaat
        )

        cls.detail_url = reverse(
            "zaak-detail",
            kwargs={
                "bronorganisatie": "123456782",
                "identificatie": "ZAAK-2020-0010",
            },
        )

    def setUp(self):
        super().setUp()

        self.patch_get_resultaat.start()
        self.addCleanup(self.patch_get_resultaat.stop)

        # ensure that we have a user with all permissions
        self.client.force_authenticate(user=self.user)

    @freeze_time("2020-12-26T12:00:00Z")
    @patch("zac.elasticsearch.api.get_zaakobjecten", return_value=[])
    def test_get_zaak_detail_indexed_in_es(self, m, *mocks):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.zaak)
        mock_resource_get(m, self.zaaktype)
        zaak_document = self.create_zaak_document(self.zaak)
        zaak_document.zaaktype = self.create_zaaktype_document(self.zaaktype)
        zaak_document.save()
        self.refresh_index()

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_response = {
            "url": f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            "identificatie": "ZAAK-2020-0010",
            "bronorganisatie": "123456782",
            "zaaktype": {
                "url": f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
                "catalogus": f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd",
                "omschrijving": self.zaaktype["omschrijving"],
                "versiedatum": self.zaaktype["versiedatum"],
            },
            "omschrijving": self.zaak["omschrijving"],
            "toelichting": self.zaak["toelichting"],
            "registratiedatum": self.zaak["registratiedatum"],
            "startdatum": "2020-12-25",
            "einddatum": None,
            "einddatumGepland": None,
            "uiterlijkeEinddatumAfdoening": "2021-01-04",
            "vertrouwelijkheidaanduiding": "openbaar",
            "deadline": "2021-01-04",
            "deadlineProgress": 10.00,
            "resultaat": self.resultaat,
        }
        self.assertEqual(response.json(), expected_response)

    @freeze_time("2020-12-26T12:00:00Z")
    def test_not_indexed_in_es(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.zaaktype)
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456782&identificatie=ZAAK-2020-0010",
            json=paginated_response([self.zaak]),
        )

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_response = {
            "url": f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            "identificatie": "ZAAK-2020-0010",
            "bronorganisatie": "123456782",
            "zaaktype": {
                "url": f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
                "catalogus": f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd",
                "omschrijving": self.zaaktype["omschrijving"],
                "versiedatum": self.zaaktype["versiedatum"],
            },
            "omschrijving": self.zaak["omschrijving"],
            "toelichting": self.zaak["toelichting"],
            "registratiedatum": self.zaak["registratiedatum"],
            "startdatum": "2020-12-25",
            "einddatum": None,
            "einddatumGepland": None,
            "uiterlijkeEinddatumAfdoening": "2021-01-04",
            "vertrouwelijkheidaanduiding": "openbaar",
            "deadline": "2021-01-04",
            "deadlineProgress": 10.00,
            "resultaat": self.resultaat,
        }
        self.assertEqual(response.json(), expected_response)

    def test_not_found(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456782&identificatie=ZAAK-2020-0010",
            json=paginated_response([]),
        )

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @freeze_time("2020-12-26T12:00:00Z")
    def test_update_zaak_detail(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.zaaktype)
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456782&identificatie=ZAAK-2020-0010",
            json=paginated_response([self.zaak]),
        )

        m.patch(self.zaak["url"], status_code=status.HTTP_200_OK)

        response = self.client.patch(
            self.detail_url,
            {
                "einddatum": "2021-01-01",
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduidingen.zeer_geheim,
                "reden": "because",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(m.last_request.url, self.zaak["url"])
        self.assertEqual(
            m.last_request.json(),
            {
                "einddatum": "2021-01-01",
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        self.assertEqual(m.last_request.headers["X-Audit-Toelichting"], "because")

    def test_update_zaak_invalid_cache(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.zaaktype)
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456782&identificatie=ZAAK-2020-0010",
            json=paginated_response([self.zaak]),
        )

        m.patch(self.zaak["url"], status_code=status.HTTP_200_OK)

        # populate cache
        get_response = self.client.get(self.detail_url)

        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        cache_find_key = (
            f"zaak:{self.zaak['bronorganisatie']}:{self.zaak['identificatie']}"
        )
        self.assertIsNotNone(cache.get(cache_find_key))

        # patch
        response = self.client.patch(
            self.detail_url,
            {
                "einddatum": "2021-01-01",
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduidingen.zeer_geheim,
                "reden": "because",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        #  cache is cleaned
        self.assertIsNone(cache.get(cache_find_key))

    @freeze_time("2020-12-26T12:00:00Z")
    def test_change_invalid(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.zaaktype)
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456782&identificatie=ZAAK-2020-0010",
            json=paginated_response([self.zaak]),
        )

        m.patch(self.zaak["url"], status_code=status.HTTP_200_OK)

        response = self.client.patch(
            self.detail_url,
            {
                "vertrouwelijkheidaanduiding": "zo-geheim-dit",
            },
        )
        self.assertEqual(response.status_code, 400)
        response = response.json()
        self.assertEqual(
            response["vertrouwelijkheidaanduiding"],
            ['"zo-geheim-dit" is een ongeldige keuze.'],
        )
        self.assertEqual(response["reden"], ["Dit veld is vereist."])


class ZaakDetailPermissionTests(ESMixin, ClearCachesMixin, APITestCase):
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
        cls._zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=catalogus_url,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT1",
        )
        cls.zaaktype = factory(ZaakType, cls._zaaktype)
        cls._zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            identificatie="ZAAK-2020-0010",
            bronorganisatie="123456782",
            zaaktype=cls.zaaktype.url,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.beperkt_openbaar,
        )
        cls.zaak = factory(Zaak, cls._zaak)
        cls.zaak.zaaktype = cls.zaaktype

        cls.find_zaak_patcher = patch(
            "zac.core.api.views.find_zaak", return_value=cls.zaak
        )

        cls.detail_url = reverse(
            "zaak-detail",
            kwargs={
                "bronorganisatie": "123456782",
                "identificatie": "ZAAK-2020-0010",
            },
        )

    def setUp(self):
        super().setUp()

        self.find_zaak_patcher.start()
        self.addCleanup(self.find_zaak_patcher.stop)

    def test_not_authenticated(self):
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.patch(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_authenticated_no_permissions(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self._zaaktype)
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie={self.zaak.bronorganisatie}&identificatie={self.zaak.identificatie}",
            json=paginated_response([self._zaak]),
        )

        user = UserFactory.create()
        self.client.force_authenticate(user=user)

        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.patch(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.json(),
            {
                "canRequestAccess": False,
                "reason": "User doesn't have permissions to request the access",
            },
        )

    @requests_mock.Mocker()
    def test_has_perm_but_not_for_zaaktype(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self._zaaktype)
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie={self.zaak.bronorganisatie}&identificatie={self.zaak.identificatie}",
            json=paginated_response([self._zaak]),
        )
        # gives them access to the page, but no catalogus specified -> nothing visible
        user = UserFactory.create()
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=user,
            policy={
                "catalogus": "",
                "zaaktype_omschrijving": "",
                "max_va": VertrouwelijkheidsAanduidingen.beperkt_openbaar,
            },
        )
        self.client.force_authenticate(user=user)

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.json(),
            {
                "canRequestAccess": False,
                "reason": "User doesn't have permissions to request the access",
            },
        )

    @requests_mock.Mocker()
    def test_has_perm_but_not_for_va(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self._zaaktype)
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie={self.zaak.bronorganisatie}&identificatie={self.zaak.identificatie}",
            json=paginated_response([self._zaak]),
        )
        user = UserFactory.create()
        # gives them access to the page and zaaktype, but insufficient VA
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=user,
            policy={
                "catalogus": self.zaaktype.catalogus,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.openbaar,
            },
        )
        self.client.force_authenticate(user=user)

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.json(),
            {
                "canRequestAccess": False,
                "reason": "User doesn't have permissions to request the access",
            },
        )

    @requests_mock.Mocker()
    def test_has_no_perm_can_request(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self._zaaktype)
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie={self.zaak.bronorganisatie}&identificatie={self.zaak.identificatie}",
            json=paginated_response([self._zaak]),
        )
        user = UserFactory.create()
        # gives them access to the page and zaaktype, but insufficient VA
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_request_access.name],
            for_user=user,
            policy={
                "catalogus": self.zaaktype.catalogus,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        self.client.force_authenticate(user=user)

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.json()["canRequestAccess"], True)

    @requests_mock.Mocker()
    def test_has_no_perm_already_requested(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self._zaaktype)
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie={self.zaak.bronorganisatie}&identificatie={self.zaak.identificatie}",
            json=paginated_response([self._zaak]),
        )
        user = UserFactory.create()
        # gives them access to the page and zaaktype, but insufficient VA
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_request_access.name],
            for_user=user,
            policy={
                "catalogus": self.zaaktype.catalogus,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        AccessRequestFactory.create(requester=user, zaak=self.zaak.url)
        self.client.force_authenticate(user=user)

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.json(),
            {
                "canRequestAccess": False,
                "reason": "User has pending access request for this zaak",
            },
        )

    @requests_mock.Mocker()
    def test_has_perm_to_retrieve(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype.catalogus}",
            json=paginated_response([self._zaaktype]),
        )
        user = UserFactory.create()
        # gives them access to the page, zaaktype and VA specified -> visible
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=user,
            policy={
                "catalogus": self.zaaktype.catalogus,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            },
        )
        self.client.force_authenticate(user=user)

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @requests_mock.Mocker()
    def test_has_perm_to_update(self, m):

        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype.catalogus}",
            json=paginated_response([self._zaaktype]),
        )
        user = UserFactory.create()

        # allows them to update details on the case
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_wijzigen.name],
            for_user=user,
            policy={
                "catalogus": self.zaaktype.catalogus,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            },
        )
        self.client.force_authenticate(user=user)

        m.patch(self.zaak.url, status_code=status.HTTP_200_OK)
        response = self.client.patch(
            self.detail_url,
            {
                "einddatum": "2021-01-01",
                "vertrouwelijkheidaanduiding": VertrouwelijkheidsAanduidingen.zeer_geheim,
                "reden": "because",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    @requests_mock.Mocker()
    def test_has_atomic_access(self, m):
        user = UserFactory.create()
        AtomicPermissionFactory.create(
            object_url=self.zaak.url,
            permission=zaken_inzien.name,
            for_user=user,
        )
        self.client.force_authenticate(user=user)

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
