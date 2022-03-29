from django.urls import reverse_lazy

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.models import APITypes, Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import UserFactory
from zac.core.tests.utils import ClearCachesMixin

from ..models import ChecklistType
from .factories import ChecklistTypeFactory

ZAKEN_ROOT = "https://open-zaak.nl/zaken/api/v1/"
CATALOGI_ROOT = "https://open-zaak.nl/catalogi/api/v1/"


class ListChecklistTypesPermissionTests(ClearCachesMixin, APITestCase):
    """
    Test the checklist list endpoint permissions.

    """

    endpoint = reverse_lazy("checklisttype-list")

    def test_list_not_logged_in(self):
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_logged_in_no_staff_member(self):
        user = UserFactory.create(is_staff=False)
        self.client.force_authenticate(user)
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_logged_in_staff_member(self):
        user = UserFactory.create(is_staff=True)
        self.client.force_authenticate(user)
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class RetrieveChecklistTypesPermissionTests(ClearCachesMixin, APITestCase):
    """
    Test the checklisttype retrieve endpoint permissions.

    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.checklisttype = ChecklistTypeFactory.create(
            zaaktype="https://some-zt-url.com/",
            zaaktype_omschrijving="omschrijving",
            zaaktype_catalogus="https://some-catalogus-url.com/",
        )
        cls.endpoint = reverse_lazy(
            "checklisttype-detail", kwargs={"pk": cls.checklisttype.pk}
        )

    def test_read_not_logged_in(self):
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_read_logged_in_no_staff_member(self):
        user = UserFactory.create(is_staff=False)
        self.client.force_authenticate(user)
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_read_logged_in_staff_member(self):
        user = UserFactory.create(is_staff=True)
        self.client.force_authenticate(user)
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class CreateChecklistTypesPermissionTests(ClearCachesMixin, APITestCase):
    """
    Test the checklisttype create endpoint permissions.

    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.endpoint = reverse_lazy("checklisttype-list")

    def test_create_not_logged_in(self):
        response = self.client.post(self.endpoint, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_logged_in_not_admin(self):
        user = UserFactory.create(is_staff=False)
        self.client.force_authenticate(user)
        response = self.client.post(self.endpoint, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_create_logged_in_as_admin(self, m):
        Service.objects.create(
            label="Catalogi API",
            api_type=APITypes.ztc,
            api_root=CATALOGI_ROOT,
        )
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        catalogus = f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            catalogus=catalogus,
            url=f"{CATALOGI_ROOT}zaaktypen/d66790b7-8b01-4005-a4ba-8fcf2a60f21d",
            identificatie="ZT1",
            omschrijving="ZT1",
        )
        m.get(zaaktype["url"], json=zaaktype)
        data = {
            "zaaktype": zaaktype["url"],
            "questions": [{"question": "some-question", "choices": [], "order": 1}],
        }

        user = UserFactory.create(is_staff=True)
        self.client.force_authenticate(user)
        self.assertEqual(ChecklistType.objects.all().count(), 0)
        response = self.client.post(self.endpoint, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class UpdateChecklistTypesPermissionTests(ClearCachesMixin, APITestCase):
    """
    Test the checklisttype update endpoint permissions.

    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.checklisttype = ChecklistTypeFactory.create(
            zaaktype="https://some-zaaktype-url.com/",
            zaaktype_omschrijving="some-omschrijving",
            zaaktype_catalogus="https://some-catalogus.com/",
        )
        cls.endpoint = reverse_lazy(
            "checklisttype-detail", kwargs={"pk": cls.checklisttype.pk}
        )

    def test_update_not_logged_in(self):
        response = self.client.put(self.endpoint, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_logged_in_not_admin(self):
        user = UserFactory.create(is_staff=False)
        self.client.force_authenticate(user)
        response = self.client.put(self.endpoint, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_update_logged_in_as_admin(self, m):
        Service.objects.create(
            label="Catalogi API",
            api_type=APITypes.ztc,
            api_root=CATALOGI_ROOT,
        )
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        catalogus = f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            catalogus=catalogus,
            url=f"{CATALOGI_ROOT}zaaktypen/d66790b7-8b01-4005-a4ba-8fcf2a60f21d",
            identificatie="ZT1",
            omschrijving="ZT1",
        )
        m.get(zaaktype["url"], json=zaaktype)
        data = {
            "zaaktype": zaaktype["url"],
            "questions": [{"question": "some-question", "choices": [], "order": 1}],
        }

        user = UserFactory.create(is_staff=True)
        self.client.force_authenticate(user)
        response = self.client.put(self.endpoint, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
