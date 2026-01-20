from django.urls import reverse, reverse_lazy

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes

from zac.accounts.tests.factories import (
    AtomicPermissionFactory,
    BlueprintPermissionFactory,
    UserFactory,
)
from zac.core.permissions import zaken_geforceerd_bijwerken
from zac.core.tests.utils import ClearCachesMixin
from zac.tests import ServiceFactory
from zac.tests.compat import generate_oas_component, mock_service_oas_get
from zac.tests.utils import mock_resource_get

from ..permissions import activiteiten_inzien, activiteiten_schrijven
from .factories import ActivityFactory

ZAKEN_ROOT = "https://open-zaak.nl/zaken/api/v1/"
CATALOGI_ROOT = "https://open-zaak.nl/catalogi/api/v1/"
CATALOGUS_URL = f"{CATALOGI_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"


class ListActivitiesPermissionTests(ClearCachesMixin, APITestCase):
    """
    Test the activity list endpoint permissions.

    These tests build up from top-to-bottom in increased permissions, starting with
    a user who's not logged in at all. Every test adds a little extra that satisfies
    the previous test, until eventually permissions are effectively set and a succesful,
    auth controlled read is performed.
    """

    endpoint = reverse_lazy("activity-list")

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        ServiceFactory.create(
            label="Zaken API", api_type=APITypes.zrc, api_root=ZAKEN_ROOT
        )
        ServiceFactory.create(
            label="Catalogi API",
            api_type=APITypes.ztc,
            api_root=CATALOGI_ROOT,
        )
        cls.catalogus = generate_oas_component(
            "ztc",
            "schemas/Catalogus",
            url=CATALOGUS_URL,
            domein="DOME",
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            catalogus=CATALOGUS_URL,
            url=f"{CATALOGI_ROOT}zaaktypen/d66790b7-8b01-4005-a4ba-8fcf2a60f21d",
            identificatie="ZT1",
            omschrijving="ZT1",
        )

        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7",
            zaaktype=cls.zaaktype["url"],
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
        mock_resource_get(m, self.zaak)

        response = self.client.get(self.endpoint, {"zaak": self.zaak["url"]})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_read_logged_in_permissions_for_other_zaak(self, m):
        user = UserFactory.create()
        self.client.force_authenticate(user)
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.zaak)

        # set up user permissions
        BlueprintPermissionFactory.create(
            role__permissions=[activiteiten_inzien.name],
            for_user=user,
            policy={
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT2",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        response = self.client.get(self.endpoint, {"zaak": self.zaak["url"]})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_read_logged_in_zaak_permission(self, m):
        user = UserFactory.create()
        self.client.force_authenticate(user)
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.zaak)

        # set up user permissions
        BlueprintPermissionFactory.create(
            role__permissions=[activiteiten_inzien.name],
            for_user=user,
            policy={
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        # set up test data
        ActivityFactory.create()
        activity = ActivityFactory.create(zaak=self.zaak["url"])

        response = self.client.get(self.endpoint, {"zaak": self.zaak["url"]})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        self.assertEqual(response.data[0]["id"], activity.id)

    @requests_mock.Mocker()
    def test_read_logged_in_zaak_permission_atomic(self, m):
        user = UserFactory.create()
        self.client.force_authenticate(user)
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaak)

        # set up user permissions
        AtomicPermissionFactory.create(
            for_user=user,
            permission=activiteiten_inzien.name,
            object_url=self.zaak["url"],
        )

        # set up test data
        ActivityFactory.create()
        activity = ActivityFactory.create(zaak=self.zaak["url"])

        response = self.client.get(self.endpoint, {"zaak": self.zaak["url"]})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        self.assertEqual(response.data[0]["id"], activity.id)


class ReadActivityDetailPermissionTests(ClearCachesMixin, APITestCase):
    """
    Test the activity detail endpoint permissions.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        ServiceFactory.create(
            label="Zaken API", api_type=APITypes.zrc, api_root=ZAKEN_ROOT
        )
        ServiceFactory.create(
            label="Catalogi API",
            api_type=APITypes.ztc,
            api_root=CATALOGI_ROOT,
        )

        cls.catalogus = generate_oas_component(
            "ztc",
            "schemas/Catalogus",
            url=CATALOGUS_URL,
            domein="DOME",
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            catalogus=CATALOGUS_URL,
            url=f"{CATALOGI_ROOT}zaaktypen/d66790b7-8b01-4005-a4ba-8fcf2a60f21d",
            identificatie="ZT1",
            omschrijving="ZT1",
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
        endpoint = reverse("activity-detail", kwargs={"pk": self.activity.pk})

        response = self.client.get(endpoint)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_read_logged_in_no_permissions(self, m):
        endpoint = reverse("activity-detail", kwargs={"pk": self.activity.pk})
        self.client.force_authenticate(self.user)
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.zaak)

        response = self.client.get(endpoint)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_read_logged_in_with_permissions_for_another_zaak(self, m):
        endpoint = reverse("activity-detail", kwargs={"pk": self.activity.pk})
        self.client.force_authenticate(self.user)
        # set up user permissions
        BlueprintPermissionFactory.create(
            role__permissions=[activiteiten_inzien.name],
            for_user=self.user,
            policy={
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT2",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.zaak)

        response = self.client.get(endpoint)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_read_logged_in_with_permissions(self, m):
        endpoint = reverse("activity-detail", kwargs={"pk": self.activity.pk})
        self.client.force_authenticate(self.user)
        # set up user permissions
        BlueprintPermissionFactory.create(
            role__permissions=[activiteiten_inzien.name],
            for_user=self.user,
            policy={
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.zaak)

        response = self.client.get(endpoint)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @requests_mock.Mocker()
    def test_read_logged_in_with_atomic_permissions(self, m):
        endpoint = reverse("activity-detail", kwargs={"pk": self.activity.pk})
        self.client.force_authenticate(self.user)
        # set up user permissions
        AtomicPermissionFactory.create(
            permission=activiteiten_inzien.name,
            for_user=self.user,
            object_url=self.zaak["url"],
        )
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaak)

        response = self.client.get(endpoint)

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class CreatePermissionTests(ClearCachesMixin, APITestCase):
    endpoint = reverse_lazy("activity-list")

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        ServiceFactory.create(
            label="Zaken API", api_type=APITypes.zrc, api_root=ZAKEN_ROOT
        )
        ServiceFactory.create(
            label="Catalogi API",
            api_type=APITypes.ztc,
            api_root=CATALOGI_ROOT,
        )

        cls.catalogus = generate_oas_component(
            "ztc",
            "schemas/Catalogus",
            url=CATALOGUS_URL,
            domein="DOME",
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            catalogus=CATALOGUS_URL,
            url=f"{CATALOGI_ROOT}zaaktypen/d66790b7-8b01-4005-a4ba-8fcf2a60f21d",
            identificatie="ZT1",
            omschrijving="ZT1",
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
        mock_resource_get(m, self.zaak)
        data = {
            "zaak": self.zaak["url"],
            "name": "Dummy",
        }

        response = self.client.post(self.endpoint, data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_create_activity_logged_in_with_permissions_for_other_zaak(self, m):
        self.client.force_authenticate(user=self.user)
        # set up user permissions
        BlueprintPermissionFactory.create(
            role__permissions=[activiteiten_schrijven.name],
            for_user=self.user,
            policy={
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT2",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.zaak)
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
        BlueprintPermissionFactory.create(
            role__permissions=[activiteiten_schrijven.name],
            for_user=self.user,
            policy={
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.zaak)
        data = {
            "zaak": self.zaak["url"],
            "name": "Dummy",
        }

        response = self.client.post(self.endpoint, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @requests_mock.Mocker()
    def test_create_activity_logged_in_with_atomic_permissions(self, m):
        self.client.force_authenticate(user=self.user)
        # set up user permissions
        AtomicPermissionFactory.create(
            permission=activiteiten_schrijven.name,
            for_user=self.user,
            object_url=self.zaak["url"],
        )

        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaak)
        data = {
            "zaak": self.zaak["url"],
            "name": "Dummy",
        }

        response = self.client.post(self.endpoint, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_event_not_logged_in(self):
        endpoint = reverse_lazy("event-list")

        response = self.client.post(endpoint)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_create_event_logged_in_no_permissions(self, m):
        endpoint = reverse_lazy("event-list")
        activity = ActivityFactory.create(zaak=self.zaak["url"])
        self.client.force_authenticate(user=self.user)
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.zaak)
        data = {
            "activity": activity.id,
            "notes": "Test notes",
        }

        response = self.client.post(endpoint, data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_create_event_logged_in_with_permissions_for_other_zaak(self, m):
        endpoint = reverse_lazy("event-list")
        activity = ActivityFactory.create(zaak=self.zaak["url"])
        self.client.force_authenticate(user=self.user)
        # set up user permissions
        BlueprintPermissionFactory.create(
            role__permissions=[activiteiten_schrijven.name],
            for_user=self.user,
            policy={
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT2",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.zaak)
        data = {
            "activity": activity.id,
            "notes": "Test notes",
        }

        response = self.client.post(endpoint, data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_create_event_logged_in_with_permissions(self, m):
        endpoint = reverse_lazy("event-list")
        activity = ActivityFactory.create(zaak=self.zaak["url"])
        self.client.force_authenticate(user=self.user)
        # set up user permissions
        BlueprintPermissionFactory.create(
            role__permissions=[activiteiten_schrijven.name],
            for_user=self.user,
            policy={
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.zaak)
        data = {
            "activity": activity.id,
            "notes": "Test notes",
        }

        response = self.client.post(endpoint, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @requests_mock.Mocker()
    def test_create_event_logged_in_with_permissions_but_not_for_closed_zaak(self, m):
        endpoint = reverse_lazy("event-list")
        activity = ActivityFactory.create(zaak=self.zaak["url"])
        self.client.force_authenticate(user=self.user)
        # set up user permissions
        BlueprintPermissionFactory.create(
            role__permissions=[activiteiten_schrijven.name],
            for_user=self.user,
            policy={
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.zaaktype)
        m.get(self.zaak["url"], json={**self.zaak, "einddatum": "2020-01-01"})
        data = {
            "activity": activity.id,
            "notes": "Test notes",
        }

        response = self.client.post(endpoint, data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_create_event_logged_in_with_permissions_also_for_closed_zaak(self, m):
        endpoint = reverse_lazy("event-list")
        activity = ActivityFactory.create(zaak=self.zaak["url"])
        self.client.force_authenticate(user=self.user)
        # set up user permissions
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_geforceerd_bijwerken.name],
            for_user=self.user,
            policy={
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        BlueprintPermissionFactory.create(
            role__permissions=[activiteiten_schrijven.name],
            for_user=self.user,
            policy={
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.zaaktype)
        m.get(self.zaak["url"], json={**self.zaak, "einddatum": "2020-01-01"})
        data = {
            "activity": activity.id,
            "notes": "Test notes",
        }

        response = self.client.post(endpoint, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @requests_mock.Mocker()
    def test_create_event_logged_in_with_atomic_permissions(self, m):
        endpoint = reverse_lazy("event-list")
        activity = ActivityFactory.create(zaak=self.zaak["url"])
        self.client.force_authenticate(user=self.user)
        # set up user permissions
        AtomicPermissionFactory.create(
            permission=activiteiten_schrijven.name,
            for_user=self.user,
            object_url=self.zaak["url"],
        )

        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaak)
        data = {
            "activity": activity.id,
            "notes": "Test notes",
        }

        response = self.client.post(endpoint, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @requests_mock.Mocker()
    def test_create_event_logged_in_with_atomic_permissions_but_not_for_closed_zaak(
        self, m
    ):
        endpoint = reverse_lazy("event-list")
        activity = ActivityFactory.create(zaak=self.zaak["url"])
        self.client.force_authenticate(user=self.user)
        # set up user permissions
        AtomicPermissionFactory.create(
            permission=activiteiten_schrijven.name,
            for_user=self.user,
            object_url=self.zaak["url"],
        )

        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        m.get(self.zaak["url"], json={**self.zaak, "einddatum": "2020-01-01"})
        data = {
            "activity": activity.id,
            "notes": "Test notes",
        }

        response = self.client.post(endpoint, data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_create_event_logged_in_with_atomic_permissions_also_for_closed_zaak(
        self, m
    ):
        endpoint = reverse_lazy("event-list")
        activity = ActivityFactory.create(zaak=self.zaak["url"])
        self.client.force_authenticate(user=self.user)
        # set up user permissions
        AtomicPermissionFactory.create(
            permission=zaken_geforceerd_bijwerken.name,
            for_user=self.user,
            object_url=self.zaak["url"],
        )
        AtomicPermissionFactory.create(
            permission=activiteiten_schrijven.name,
            for_user=self.user,
            object_url=self.zaak["url"],
        )

        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        m.get(self.zaak["url"], json={**self.zaak, "einddatum": "2020-01-01"})
        data = {
            "activity": activity.id,
            "notes": "Test notes",
        }

        response = self.client.post(endpoint, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class UpdatePermissionTests(ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        ServiceFactory.create(
            label="Zaken API", api_type=APITypes.zrc, api_root=ZAKEN_ROOT
        )
        ServiceFactory.create(
            label="Catalogi API",
            api_type=APITypes.ztc,
            api_root=CATALOGI_ROOT,
        )
        cls.catalogus = generate_oas_component(
            "ztc",
            "schemas/Catalogus",
            url=CATALOGUS_URL,
            domein="DOME",
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            catalogus=CATALOGUS_URL,
            url=f"{CATALOGI_ROOT}zaaktypen/d66790b7-8b01-4005-a4ba-8fcf2a60f21d",
            identificatie="ZT1",
            omschrijving="ZT1",
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

    def test_update_activity_not_logged_in(self):
        endpoint = reverse("activity-detail", kwargs={"pk": self.activity.pk})

        response = self.client.patch(endpoint, {})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_update_activity_logged_in_no_permission(self, m):
        endpoint = reverse("activity-detail", kwargs={"pk": self.activity.pk})
        self.client.force_authenticate(user=self.user)
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.zaak)
        data = {"name": "New name"}

        response = self.client.patch(endpoint, data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_update_activity_logged_in_with_permissions_for_other_zaak(self, m):
        endpoint = reverse("activity-detail", kwargs={"pk": self.activity.pk})
        self.client.force_authenticate(user=self.user)
        # set up user permissions
        BlueprintPermissionFactory.create(
            role__permissions=[activiteiten_schrijven.name],
            for_user=self.user,
            policy={
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT2",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.zaak)
        data = {"name": "New name"}

        response = self.client.patch(endpoint, data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_update_activity_logged_in_with_permissions(self, m):
        endpoint = reverse("activity-detail", kwargs={"pk": self.activity.pk})
        self.client.force_authenticate(user=self.user)
        # set up user permissions
        BlueprintPermissionFactory.create(
            role__permissions=[activiteiten_schrijven.name],
            for_user=self.user,
            policy={
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.zaak)
        data = {"name": "New name"}

        response = self.client.patch(endpoint, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @requests_mock.Mocker()
    def test_update_activity_logged_in_with_permissions_but_not_for_closed_zaak(
        self, m
    ):
        endpoint = reverse("activity-detail", kwargs={"pk": self.activity.pk})
        self.client.force_authenticate(user=self.user)
        # set up user permissions
        BlueprintPermissionFactory.create(
            role__permissions=[activiteiten_schrijven.name],
            for_user=self.user,
            policy={
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.zaaktype)
        m.get(self.zaak["url"], json={**self.zaak, "einddatum": "2020-01-01"})
        data = {"name": "New name"}

        response = self.client.patch(endpoint, data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_update_activity_logged_in_with_permissions_also_for_closed_zaak(self, m):
        endpoint = reverse("activity-detail", kwargs={"pk": self.activity.pk})
        self.client.force_authenticate(user=self.user)
        # set up user permissions
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_geforceerd_bijwerken.name],
            for_user=self.user,
            policy={
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        BlueprintPermissionFactory.create(
            role__permissions=[activiteiten_schrijven.name],
            for_user=self.user,
            policy={
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.zaaktype)
        m.get(self.zaak["url"], json={**self.zaak, "einddatum": "2020-01-01"})
        data = {"name": "New name"}

        response = self.client.patch(endpoint, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @requests_mock.Mocker()
    def test_update_activity_logged_in_with_atomic_permissions(self, m):
        endpoint = reverse("activity-detail", kwargs={"pk": self.activity.pk})
        self.client.force_authenticate(user=self.user)
        # set up user permissions
        AtomicPermissionFactory.create(
            permission=activiteiten_schrijven.name,
            for_user=self.user,
            object_url=self.zaak["url"],
        )
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaak)
        data = {"name": "New name"}

        response = self.client.patch(endpoint, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @requests_mock.Mocker()
    def test_update_activity_logged_in_with_atomic_permissions_not_for_closed_zaak(
        self, m
    ):
        endpoint = reverse("activity-detail", kwargs={"pk": self.activity.pk})
        self.client.force_authenticate(user=self.user)
        # set up user permissions
        AtomicPermissionFactory.create(
            permission=activiteiten_schrijven.name,
            for_user=self.user,
            object_url=self.zaak["url"],
        )
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        m.get(self.zaak["url"], json={**self.zaak, "einddatum": "2020-01-01"})
        data = {"name": "New name"}

        response = self.client.patch(endpoint, data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_update_activity_logged_in_with_atomic_permissions_also_for_closed_zaak(
        self, m
    ):
        endpoint = reverse("activity-detail", kwargs={"pk": self.activity.pk})
        self.client.force_authenticate(user=self.user)
        # set up user permissions
        AtomicPermissionFactory.create(
            permission=zaken_geforceerd_bijwerken.name,
            for_user=self.user,
            object_url=self.zaak["url"],
        )
        AtomicPermissionFactory.create(
            permission=activiteiten_schrijven.name,
            for_user=self.user,
            object_url=self.zaak["url"],
        )
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        m.get(self.zaak["url"], json={**self.zaak, "einddatum": "2020-01-01"})
        data = {"name": "New name"}

        response = self.client.patch(endpoint, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
