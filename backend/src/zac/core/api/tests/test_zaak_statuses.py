from unittest.mock import patch

from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse

import requests_mock
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
from zac.contrib.kownsl.models import KownslConfig
from zac.core.permissions import zaken_inzien
from zac.core.tests.utils import ClearCachesMixin
from zac.tests.utils import paginated_response
from zgw.models.zrc import Zaak

CATALOGI_ROOT = "http://catalogus.nl/api/v1/"
ZAKEN_ROOT = "http://zaken.nl/api/v1/"
KOWNSL_ROOT = "https://kownsl.nl/"


@requests_mock.Mocker()
class ZaakStatusesResponseTests(ClearCachesMixin, APITestCase):
    """
    Test the API response body for zaak-statuses endpoint.
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
        cls.statustype_1 = generate_oas_component(
            "ztc",
            "schemas/StatusType",
            url=f"{CATALOGI_ROOT}statustypen/81cede80-ef69-40e7-b5a1-f5723b586002",
            zaaktype=cls.zaaktype["url"],
            volgnummer=1,
        )
        cls.statustype_2 = generate_oas_component(
            "ztc",
            "schemas/StatusType",
            url=f"{CATALOGI_ROOT}statustypen/486f83e6-f841-462c-aa3b-f3d0f4d72870",
            zaaktype=cls.zaaktype["url"],
            volgnummer=2,
        )
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            identificatie="ZAAK-2020-0010",
            bronorganisatie="123456782",
            zaaktype=cls.zaaktype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
        )

        zaak = factory(Zaak, cls.zaak)
        zaak.zaaktype = factory(ZaakType, cls.zaaktype)

        cls.find_zaak_patcher = patch("zac.core.api.views.find_zaak", return_value=zaak)

        cls.endpoint = reverse(
            "zaak-statuses",
            kwargs={
                "bronorganisatie": "123456782",
                "identificatie": "ZAAK-2020-0010",
            },
        )

    def setUp(self):
        super().setUp()

        self.find_zaak_patcher.start()
        self.addCleanup(self.find_zaak_patcher.stop)

        # ensure that we have a user with all permissions
        self.client.force_authenticate(user=self.user)

    def test_no_statuses(self, m):
        with patch("zac.core.api.views.get_statussen", return_value=[]):
            response = self.client.get(self.endpoint)

        self.assertEqual(response.data, [])

    def test_multiple_statuses(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        status_1 = generate_oas_component(
            "zrc",
            "schemas/Status",
            url=f"{ZAKEN_ROOT}statussen/bdab0b31-83b6-452c-9311-9bf40f519de6",
            zaak=self.zaak["url"],
            statustype=self.statustype_1["url"],
            datumStatusGezet="2020-12-25T00:00:00Z",
        )
        status_2 = generate_oas_component(
            "zrc",
            "schemas/Status",
            url=f"{ZAKEN_ROOT}statussen/bdab0b31-83b6-452c-9311-9bf40f519de6",
            zaak=self.zaak["url"],
            statustype=self.statustype_2["url"],
            datumStatusGezet="2020-12-26T00:00:00Z",
        )
        m.get(
            f"{CATALOGI_ROOT}statustypen?zaaktype={self.zaaktype['url']}",
            json=paginated_response([self.statustype_1, self.statustype_2]),
        )
        m.get(
            f"{ZAKEN_ROOT}statussen?zaak={self.zaak['url']}",
            json=paginated_response([status_1, status_2]),
        )

        response = self.client.get(self.endpoint)

        response_data = response.json()
        self.assertEqual(len(response_data), 2)
        self.assertEqual(response_data[0]["datumStatusGezet"], "2020-12-26T00:00:00Z")
        self.assertEqual(response_data[0]["statustype"]["volgnummer"], 2)

        self.assertEqual(response_data[1]["datumStatusGezet"], "2020-12-25T00:00:00Z")
        self.assertEqual(response_data[1]["statustype"]["volgnummer"], 1)

        self.assertEqual(
            set(response_data[0].keys()),
            {"url", "datumStatusGezet", "statustoelichting", "statustype"},
        )
        self.assertEqual(
            set(response_data[0]["statustype"].keys()),
            {
                "url",
                "omschrijving",
                "omschrijvingGeneriek",
                "statustekst",
                "volgnummer",
                "isEindstatus",
            },
        )

    def test_not_found(self, m):
        with patch("zac.core.api.views.find_zaak", side_effect=ObjectDoesNotExist):
            response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class ZaakStatusPermissiontests(ClearCachesMixin, APITestCase):
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
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
        )
        cls.statustype_1 = generate_oas_component(
            "ztc",
            "schemas/StatusType",
            url=f"{CATALOGI_ROOT}statustypen/81cede80-ef69-40e7-b5a1-f5723b586002",
            zaaktype=cls.zaaktype["url"],
            volgnummer=1,
        )
        cls.statustype_2 = generate_oas_component(
            "ztc",
            "schemas/StatusType",
            url=f"{CATALOGI_ROOT}statustypen/486f83e6-f841-462c-aa3b-f3d0f4d72870",
            zaaktype=cls.zaaktype["url"],
            volgnummer=2,
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
        cls.get_statuses_patcher = patch(
            "zac.core.api.views.get_statussen", return_value=[]
        )

        cls.endpoint = reverse(
            "zaak-statuses",
            kwargs={
                "bronorganisatie": "123456782",
                "identificatie": "ZAAK-2020-0010",
            },
        )

    def setUp(self):
        super().setUp()

        self.find_zaak_patcher.start()
        self.addCleanup(self.find_zaak_patcher.stop)

        self.get_statuses_patcher.start()
        self.addCleanup(self.get_statuses_patcher.stop)

    def test_not_authenticated(self):
        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_no_permissions(self):
        user = UserFactory.create()
        self.client.force_authenticate(user=user)

        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_has_perm_but_not_for_zaaktype(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, KOWNSL_ROOT, "kownsl")
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}",
            json=paginated_response([]),
        )
        m.get(
            f"{KOWNSL_ROOT}api/v1/review-requests?for_zaak={self.zaak['url']}",
            json=[],
        )
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
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, KOWNSL_ROOT, "kownsl")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}",
            json=paginated_response([]),
        )
        m.get(
            f"{KOWNSL_ROOT}api/v1/review-requests?for_zaak={self.zaak['url']}",
            json=[],
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
