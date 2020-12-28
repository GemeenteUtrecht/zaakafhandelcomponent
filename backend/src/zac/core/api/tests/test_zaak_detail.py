from unittest.mock import patch

from django.urls import reverse

import requests_mock
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
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
from zac.elasticsearch.tests.utils import ESMixin
from zac.tests.utils import mock_resource_get, paginated_response
from zgw.models.zrc import Zaak

CATALOGI_ROOT = "http://catalogus.nl/api/v1/"
ZAKEN_ROOT = "http://zaken.nl/api/v1/"


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

        cls.detail_url = reverse(
            "zaak-detail",
            kwargs={
                "bronorganisatie": "123456782",
                "identificatie": "ZAAK-2020-0010",
            },
        )

    def setUp(self):
        super().setUp()

        # ensure that we have a user with all permissions
        self.client.force_authenticate(user=self.user)

    @freeze_time("2020-12-26T12:00:00Z")
    def test_get_zaak_detail_indexed_in_es(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.zaak)
        mock_resource_get(m, self.zaaktype)
        self.create_zaak_document(self.zaak)
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


class ZaakDetailPermissionTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)

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
        )
        cls.zaaktype = factory(ZaakType, cls._zaaktype)
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            identificatie="ZAAK-2020-0010",
            bronorganisatie="123456782",
            zaaktype=cls.zaaktype.url,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.beperkt_openbaar,
        )
        cls.zaak = factory(Zaak, zaak)
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

    def test_authenticated_no_permissions(self):
        user = UserFactory.create()
        self.client.force_authenticate(user=user)

        response = self.client.get(self.detail_url)

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

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_has_perm_but_not_for_va(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype.catalogus}",
            json=paginated_response([self._zaaktype]),
        )
        user = UserFactory.create()
        # gives them access to the page and zaaktype, but insufficient VA
        PermissionSetFactory.create(
            permissions=[zaken_inzien.name],
            for_user=user,
            catalogus=self.zaaktype.catalogus,
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.openbaar,
        )
        self.client.force_authenticate(user=user)

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_has_perm(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype.catalogus}",
            json=paginated_response([self._zaaktype]),
        )
        user = UserFactory.create()
        # gives them access to the page, zaaktype and VA specified -> visible
        PermissionSetFactory.create(
            permissions=[zaken_inzien.name],
            for_user=user,
            catalogus=self.zaaktype.catalogus,
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
        )
        self.client.force_authenticate(user=user)

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
