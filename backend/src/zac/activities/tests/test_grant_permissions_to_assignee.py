from django.urls import reverse

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.constants import APITypes

from zac.accounts.constants import PermissionReason
from zac.accounts.models import AtomicPermission
from zac.accounts.tests.factories import GroupFactory, SuperUserFactory, UserFactory
from zac.core.permissions import zaken_inzien
from zac.core.tests.utils import ClearCachesMixin
from zac.tests import ServiceFactory
from zac.tests.compat import generate_oas_component, mock_service_oas_get
from zac.tests.utils import mock_resource_get

from ..permissions import activiteiten_inzien, activiteiten_schrijven
from .factories import ActivityFactory

ZAKEN_ROOT = "https://open-zaak.nl/zaken/api/v1/"
ZAAK_URL = f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7"


@requests_mock.Mocker()
class GrantActivityPermissionTests(ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        ServiceFactory.create(
            label="Zaken API", api_type=APITypes.zrc, api_root=ZAKEN_ROOT
        )
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=ZAAK_URL,
        )

        cls.user = SuperUserFactory.create()
        cls.assignee = UserFactory.create()
        cls.group = GroupFactory.create()
        cls.assignee.groups.add(cls.group)

    def setUp(self):
        super().setUp()

        self.client.force_login(self.user)

    def test_create_activity_without_assignee(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaak)
        endpoint = reverse("activity-list")
        data = {
            "zaak": ZAAK_URL,
            "name": "Dummy",
        }

        response = self.client.post(endpoint, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AtomicPermission.objects.count(), 0)

    def test_create_activity_with_assignee(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaak)

        self.assertEqual(AtomicPermission.objects.for_user(self.assignee).count(), 0)

        endpoint = reverse("activity-list")
        data = {
            "zaak": ZAAK_URL,
            "name": "Dummy",
            "user_assignee": self.assignee.username,
        }

        response = self.client.post(endpoint, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AtomicPermission.objects.for_user(self.assignee).count(), 3)

        permission_zaak, permission_read, permission_write = list(
            AtomicPermission.objects.for_user(self.assignee).all()
        )
        self.assertEqual(permission_zaak.permission, zaken_inzien.name)
        self.assertEqual(permission_read.permission, activiteiten_inzien.name)
        self.assertEqual(permission_write.permission, activiteiten_schrijven.name)

        for permission in [permission_zaak, permission_read, permission_write]:
            self.assertEqual(permission.object_url, ZAAK_URL)
            user_atomic_permission = permission.useratomicpermission_set.get()
            self.assertEqual(user_atomic_permission.reason, PermissionReason.activiteit)

    def test_create_activity_with_group_assignement(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaak)
        self.assertEqual(AtomicPermission.objects.for_user(self.assignee).count(), 0)

        endpoint = reverse("activity-list")
        data = {
            "zaak": ZAAK_URL,
            "name": "Dummy",
            "group_assignee": self.group.name,
        }

        response = self.client.post(endpoint, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AtomicPermission.objects.for_user(self.assignee).count(), 3)

        permission_zaak, permission_read, permission_write = list(
            AtomicPermission.objects.for_user(self.assignee).all()
        )
        self.assertEqual(permission_zaak.permission, zaken_inzien.name)
        self.assertEqual(permission_read.permission, activiteiten_inzien.name)
        self.assertEqual(permission_write.permission, activiteiten_schrijven.name)

        for permission in [permission_zaak, permission_read, permission_write]:
            self.assertEqual(permission.object_url, ZAAK_URL)
            user_atomic_permission = permission.useratomicpermission_set.get()
            self.assertEqual(user_atomic_permission.reason, PermissionReason.activiteit)

    def test_update_activity_change_assignee(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaak)
        activity = ActivityFactory.create(zaak=ZAAK_URL)
        self.assertEqual(AtomicPermission.objects.for_user(self.assignee).count(), 0)

        endpoint = reverse("activity-detail", args=[activity.id])
        data = {"user_assignee": self.assignee.username}

        response = self.client.patch(endpoint, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(AtomicPermission.objects.for_user(self.assignee).count(), 3)

        permission_zaak, permission_read, permission_write = list(
            AtomicPermission.objects.for_user(self.assignee).all()
        )
        self.assertEqual(permission_zaak.permission, zaken_inzien.name)
        self.assertEqual(permission_read.permission, activiteiten_inzien.name)
        self.assertEqual(permission_write.permission, activiteiten_schrijven.name)

        for permission in [permission_zaak, permission_read, permission_write]:
            self.assertEqual(permission.object_url, ZAAK_URL)
            user_atomic_permission = permission.useratomicpermission_set.get()
            self.assertEqual(user_atomic_permission.reason, PermissionReason.activiteit)
