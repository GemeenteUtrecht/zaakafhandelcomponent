from django.urls import reverse, reverse_lazy

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.models import APITypes, Service

from zac.accounts.tests.factories import PermissionSetFactory, UserFactory
from zac.core.permissions import zaken_inzien
from zac.core.tests.utils import ClearCachesMixin
from zac.tests.utils import generate_oas_component, mock_service_oas_get

from ..permissions import activiteiten_schrijven
from .factories import ActivityFactory

ZAKEN_ROOT = "https://open-zaak.nl/zaken/api/v1/"
CATALOGI_ROOT = "https://open-zaak.nl/catalogi/api/v1/"


class ReadPermissionTests(ClearCachesMixin, APITestCase):
    """
    Test the activity list endpoint permissions.

    These tests build up from top-to-bottom in increased permissions, starting with
    a user who's not logged in at all. Every test adds a little extra that satisfies
    the previous test, until eventually permissions are effectively set and a succesful,
    auth controlled read is performed.
    """

    endpoint = reverse_lazy("activities:activity-list")

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        Service.objects.create(
            label="Zaken API", api_type=APITypes.zrc, api_root=ZAKEN_ROOT
        )
        Service.objects.create(
            label="Catalogi API", api_type=APITypes.ztc, api_root=CATALOGI_ROOT,
        )

    def test_read_not_logged_in(self):
        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_read_logged_in_no_filter(self):
        user = UserFactory.create()
        self.client.force_authenticate(user)
        ActivityFactory.create()

        response = self.client.get(self.endpoint)

        self.assertEqual(response.data, [])

    @requests_mock.Mocker()
    def test_read_logged_in_zaak_no_permission(self, m):
        user = UserFactory.create()
        self.client.force_authenticate(user)
        ActivityFactory.create()
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7",
            zaaktype=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
        )
        m.get(zaak["url"], json=zaak)

        response = self.client.get(self.endpoint, {"zaak": zaak["url"]})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_read_logged_in_zaak_permission(self, m):
        user = UserFactory.create()
        self.client.force_authenticate(user)
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        catalogus = f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            catalogus=catalogus,
            url=f"{CATALOGI_ROOT}zaaktypen/d66790b7-8b01-4005-a4ba-8fcf2a60f21d",
            identificatie="ZT1",
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktypen",
            json={"count": 1, "previous": None, "next": None, "results": [zaaktype],},
        )
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7",
            zaaktype=zaaktype["url"],
        )
        m.get(zaak["url"], json=zaak)

        # set up user permissions
        PermissionSetFactory.create(
            permissions=[zaken_inzien.name],
            for_user=user,
            catalogus=catalogus,
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.zeer_geheim,
        )
        # set up test data
        ActivityFactory.create()
        activity = ActivityFactory.create(zaak=zaak["url"])

        response = self.client.get(self.endpoint, {"zaak": zaak["url"]})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        self.assertEqual(response.data[0]["id"], activity.id)


class DetailReadPermissionTests(ClearCachesMixin, APITestCase):
    """
    Test the activity detail endpoint permissions.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        Service.objects.create(
            label="Zaken API", api_type=APITypes.zrc, api_root=ZAKEN_ROOT
        )
        Service.objects.create(
            label="Catalogi API", api_type=APITypes.ztc, api_root=CATALOGI_ROOT,
        )

        cls.catalogus = (
            f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            catalogus=cls.catalogus,
            url=f"{CATALOGI_ROOT}zaaktypen/d66790b7-8b01-4005-a4ba-8fcf2a60f21d",
            identificatie="ZT1",
        )
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7",
            zaaktype=cls.zaaktype["url"],
        )
        cls.activity = ActivityFactory.create(zaak=cls.zaak["url"])

    def setUp(self):
        super().setUp()

        self.user = UserFactory.create()

    def test_read_not_logged_in(self):
        endpoint = reverse(
            "activities:activity-detail", kwargs={"pk": self.activity.pk}
        )

        response = self.client.get(endpoint)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_read_logged_in_no_permissions(self, m):
        endpoint = reverse(
            "activities:activity-detail", kwargs={"pk": self.activity.pk}
        )
        self.client.force_authenticate(self.user)
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
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
        m.get(self.zaak["url"], json=self.zaak)

        response = self.client.get(endpoint)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_read_logged_in_with_permissions(self, m):
        endpoint = reverse(
            "activities:activity-detail", kwargs={"pk": self.activity.pk}
        )
        self.client.force_authenticate(self.user)
        # set up user permissions
        PermissionSetFactory.create(
            permissions=[zaken_inzien.name],
            for_user=self.user,
            catalogus=self.catalogus,
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.zeer_geheim,
        )
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
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
        m.get(self.zaak["url"], json=self.zaak)

        response = self.client.get(endpoint)

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class CreatePermissionTests(ClearCachesMixin, APITestCase):
    endpoint = reverse_lazy("activities:activity-list")

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        Service.objects.create(
            label="Zaken API", api_type=APITypes.zrc, api_root=ZAKEN_ROOT
        )
        Service.objects.create(
            label="Catalogi API", api_type=APITypes.ztc, api_root=CATALOGI_ROOT,
        )

        cls.catalogus = (
            f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            catalogus=cls.catalogus,
            url=f"{CATALOGI_ROOT}zaaktypen/d66790b7-8b01-4005-a4ba-8fcf2a60f21d",
            identificatie="ZT1",
        )
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7",
            zaaktype=cls.zaaktype["url"],
        )

    def setUp(self):
        super().setUp()

        self.user = UserFactory.create()

    def test_create_activity_not_logged_in(self):
        response = self.client.post(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_create_activity_logged_in_no_permissions(self, m):
        self.client.force_authenticate(user=self.user)
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
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
        m.get(self.zaak["url"], json=self.zaak)
        data = {
            "zaak": self.zaak["url"],
            "name": "Dummy",
        }

        response = self.client.post(self.endpoint, data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_create_activity_logged_in_with_permissions(self, m):
        self.client.force_authenticate(user=self.user)
        # set up user permissions
        PermissionSetFactory.create(
            permissions=[activiteiten_schrijven.name],
            for_user=self.user,
            catalogus=self.catalogus,
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.zeer_geheim,
        )
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
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
        m.get(self.zaak["url"], json=self.zaak)
        data = {
            "zaak": self.zaak["url"],
            "name": "Dummy",
        }

        response = self.client.post(self.endpoint, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_event_not_logged_in(self):
        endpoint = reverse_lazy("activities:event-list")

        response = self.client.post(endpoint)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_create_event_logged_in_no_permissions(self, m):
        endpoint = reverse_lazy("activities:event-list")
        activity = ActivityFactory.create(zaak=self.zaak["url"])
        self.client.force_authenticate(user=self.user)
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
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
        m.get(self.zaak["url"], json=self.zaak)
        data = {
            "activity": activity.id,
            "notes": "Test notes",
        }

        response = self.client.post(endpoint, data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
