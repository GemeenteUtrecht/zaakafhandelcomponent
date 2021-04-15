from django.urls import reverse, reverse_lazy

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.models import APITypes, Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.models import AtomicPermission
from zac.accounts.tests.factories import SuperUserFactory, UserFactory
from zac.core.tests.utils import ClearCachesMixin

from ..permissions import activiteiten_schrijven, activities_read
from .factories import ActivityFactory

ZAKEN_ROOT = "https://open-zaak.nl/zaken/api/v1/"
ZAAK_URL = f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7"


class GrantActivityPermissionTests(ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        Service.objects.create(
            label="Zaken API", api_type=APITypes.zrc, api_root=ZAKEN_ROOT
        )
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=ZAAK_URL,
        )

        cls.user = SuperUserFactory.create()
        cls.assignee = UserFactory.create()

    def setUp(self):
        super().setUp()

        self.client.force_login(self.user)

    def test_create_activity_without_assignee(self):
        endpoint = reverse("activities:activity-list")
        data = {
            "zaak": ZAAK_URL,
            "name": "Dummy",
        }

        response = self.client.post(endpoint, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AtomicPermission.objects.count(), 0)

    def test_create_activity_with_assignee(self):
        self.assertEqual(AtomicPermission.objects.for_user(self.assignee).count(), 0)

        endpoint = reverse("activities:activity-list")
        data = {"zaak": ZAAK_URL, "name": "Dummy", "assignee": self.assignee.id}

        response = self.client.post(endpoint, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AtomicPermission.objects.for_user(self.assignee).count(), 2)

        permission_read, permission_write = list(
            AtomicPermission.objects.for_user(self.assignee).all()
        )
        self.assertEqual(permission_read.object_url, ZAAK_URL)
        self.assertEqual(permission_read.permission, activities_read.name)
        self.assertEqual(permission_write.object_url, ZAAK_URL)
        self.assertEqual(permission_write.permission, activiteiten_schrijven.name)

    @requests_mock.Mocker()
    def test_update_activity_change_assignee(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        m.get(self.zaak["url"], json=self.zaak)

        activity = ActivityFactory.create(zaak=ZAAK_URL)
        self.assertEqual(AtomicPermission.objects.for_user(self.assignee).count(), 0)

        endpoint = reverse("activities:activity-detail", args=[activity.id])
        data = {"assignee": self.assignee.id}

        response = self.client.patch(endpoint, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(AtomicPermission.objects.for_user(self.assignee).count(), 2)

        permission_read, permission_write = list(
            AtomicPermission.objects.for_user(self.assignee).all()
        )
        self.assertEqual(permission_read.object_url, ZAAK_URL)
        self.assertEqual(permission_read.permission, activities_read.name)
        self.assertEqual(permission_write.object_url, ZAAK_URL)
        self.assertEqual(permission_write.permission, activiteiten_schrijven.name)
