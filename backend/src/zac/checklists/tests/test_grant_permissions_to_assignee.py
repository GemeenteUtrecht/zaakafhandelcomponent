from django.urls import reverse

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.models import APITypes, Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.constants import PermissionReason
from zac.accounts.models import AtomicPermission
from zac.accounts.tests.factories import GroupFactory, SuperUserFactory, UserFactory
from zac.core.permissions import zaken_inzien
from zac.core.tests.utils import ClearCachesMixin

from ..permissions import checklists_inzien, checklists_schrijven
from .factories import ChecklistFactory, ChecklistTypeFactory

ZAKEN_ROOT = "https://open-zaak.nl/zaken/api/v1/"
ZAAK_URL = f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7"
CATALOGI_ROOT = "https://open-zaak.nl/catalogi/api/v1/"


@requests_mock.Mocker()
class GrantChecklistPermissionTests(ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        Service.objects.create(
            label="Catalogi API",
            api_type=APITypes.ztc,
            api_root=CATALOGI_ROOT,
        )
        Service.objects.create(
            label="Zaken API", api_type=APITypes.zrc, api_root=ZAKEN_ROOT
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
            omschrijving="ZT1",
        )
        cls.zaak = generate_oas_component(
            "zrc", "schemas/Zaak", url=ZAAK_URL, zaaktype=cls.zaaktype["url"]
        )
        cls.user = SuperUserFactory.create()
        cls.assignee = UserFactory.create()
        cls.group = GroupFactory.create()
        cls.assignee.groups.add(cls.group)

        cls.checklist_type = ChecklistTypeFactory.create(
            zaaktype=cls.zaaktype["url"],
            zaaktype_omschrijving=cls.zaaktype["omschrijving"],
            zaaktype_catalogus=cls.zaaktype["catalogus"],
        )

    def setUp(self):
        super().setUp()

        self.client.force_login(self.user)

    def test_create_checklist_without_assignee(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(self.zaak["url"], json=self.zaak)
        m.get(self.zaaktype["url"], json=self.zaaktype)
        endpoint = reverse("checklist-list")
        data = {
            "zaak": ZAAK_URL,
            "checklistType": self.checklist_type.pk,
            "answers": [],
        }

        response = self.client.post(endpoint, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AtomicPermission.objects.count(), 0)

    def test_create_checklist_with_assignee(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(self.zaak["url"], json=self.zaak)
        m.get(self.zaaktype["url"], json=self.zaaktype)

        self.assertEqual(AtomicPermission.objects.for_user(self.assignee).count(), 0)
        endpoint = reverse("checklist-list")
        data = {
            "zaak": ZAAK_URL,
            "checklistType": self.checklist_type.pk,
            "userAssignee": self.assignee.username,
            "answers": [],
        }

        response = self.client.post(endpoint, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AtomicPermission.objects.for_user(self.assignee).count(), 3)

        permission_zaak, permission_read, permission_write = list(
            AtomicPermission.objects.for_user(self.assignee).all()
        )
        self.assertEqual(permission_zaak.permission, zaken_inzien.name)
        self.assertEqual(permission_read.permission, checklists_inzien.name)
        self.assertEqual(permission_write.permission, checklists_schrijven.name)

        for permission in [permission_zaak, permission_read, permission_write]:
            self.assertEqual(permission.object_url, ZAAK_URL)
            user_atomic_permission = permission.useratomicpermission_set.get()
            self.assertEqual(user_atomic_permission.reason, PermissionReason.checklist)

    def test_create_checklist_with_group_assignement(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(self.zaak["url"], json=self.zaak)
        m.get(self.zaaktype["url"], json=self.zaaktype)

        self.assertEqual(AtomicPermission.objects.for_user(self.assignee).count(), 0)

        endpoint = reverse("checklist-list")
        data = {
            "zaak": ZAAK_URL,
            "checklistType": self.checklist_type.pk,
            "groupAssignee": self.group.name,
            "answers": [],
        }

        response = self.client.post(endpoint, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(AtomicPermission.objects.for_user(self.assignee).count(), 3)

        permission_zaak, permission_read, permission_write = list(
            AtomicPermission.objects.for_user(self.assignee).all()
        )
        self.assertEqual(permission_zaak.permission, zaken_inzien.name)
        self.assertEqual(permission_read.permission, checklists_inzien.name)
        self.assertEqual(permission_write.permission, checklists_schrijven.name)

        for permission in [permission_zaak, permission_read, permission_write]:
            self.assertEqual(permission.object_url, ZAAK_URL)
            user_atomic_permission = permission.useratomicpermission_set.get()
            self.assertEqual(user_atomic_permission.reason, PermissionReason.checklist)

    def test_update_checklist_change_assignee(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(self.zaak["url"], json=self.zaak)
        m.get(self.zaaktype["url"], json=self.zaaktype)

        checklist = ChecklistFactory.create(
            zaak=ZAAK_URL, checklist_type=self.checklist_type
        )
        self.assertEqual(AtomicPermission.objects.for_user(self.assignee).count(), 0)

        endpoint = reverse("checklist-detail", args=[checklist.id])
        data = {
            "zaak": ZAAK_URL,
            "checklistType": str(self.checklist_type.pk),
            "userAssignee": self.assignee.username,
            "answers": [],
        }

        response = self.client.put(endpoint, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(AtomicPermission.objects.for_user(self.assignee).count(), 3)

        permission_zaak, permission_read, permission_write = list(
            AtomicPermission.objects.for_user(self.assignee).all()
        )
        self.assertEqual(permission_zaak.permission, zaken_inzien.name)
        self.assertEqual(permission_read.permission, checklists_inzien.name)
        self.assertEqual(permission_write.permission, checklists_schrijven.name)

        for permission in [permission_zaak, permission_read, permission_write]:
            self.assertEqual(permission.object_url, ZAAK_URL)
            user_atomic_permission = permission.useratomicpermission_set.get()
            self.assertEqual(user_atomic_permission.reason, PermissionReason.checklist)
