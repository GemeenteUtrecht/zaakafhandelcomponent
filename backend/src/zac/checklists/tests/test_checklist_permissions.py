from django.urls import reverse, reverse_lazy

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.models import APITypes, Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import (
    AtomicPermissionFactory,
    BlueprintPermissionFactory,
    UserFactory,
)
from zac.core.tests.utils import ClearCachesMixin

from ..permissions import checklists_inzien, checklists_schrijven
from .factories import ChecklistFactory, ChecklistQuestionFactory, ChecklistTypeFactory

ZAKEN_ROOT = "https://open-zaak.nl/zaken/api/v1/"
CATALOGI_ROOT = "https://open-zaak.nl/catalogi/api/v1/"


class ListChecklistsPermissionTests(ClearCachesMixin, APITestCase):
    """
    Test the checklist list endpoint permissions.

    """

    endpoint = reverse_lazy("checklist-list")

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        Service.objects.create(
            label="Zaken API", api_type=APITypes.zrc, api_root=ZAKEN_ROOT
        )
        Service.objects.create(
            label="Catalogi API",
            api_type=APITypes.ztc,
            api_root=CATALOGI_ROOT,
        )

    def test_read_not_logged_in(self):
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_read_logged_in_no_filter(self):
        user = UserFactory.create()
        self.client.force_authenticate(user)
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), ["Missing the `zaak` query parameter."])

    @requests_mock.Mocker()
    def test_read_logged_in_zaak_no_permission(self, m):
        user = UserFactory.create()
        self.client.force_authenticate(user)
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
    def test_read_logged_in_permissions_for_other_zaak(self, m):
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
            omschrijving="ZT1",
        )
        m.get(zaaktype["url"], json=zaaktype)
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7",
            zaaktype=zaaktype["url"],
        )
        m.get(zaak["url"], json=zaak)
        BlueprintPermissionFactory.create(
            role__permissions=[checklists_inzien.name],
            for_user=user,
            policy={
                "catalogus": catalogus,
                "zaaktype_omschrijving": "ZT2",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
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
            omschrijving="ZT1",
        )
        m.get(zaaktype["url"], json=zaaktype)
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7",
            zaaktype=zaaktype["url"],
        )
        m.get(zaak["url"], json=zaak)
        BlueprintPermissionFactory.create(
            role__permissions=[checklists_inzien.name],
            for_user=user,
            policy={
                "catalogus": catalogus,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        # set up test data
        ChecklistFactory.create(zaak="https://some-other-zaak-url.com")
        ChecklistFactory.create(zaak=zaak["url"])
        response = self.client.get(self.endpoint, {"zaak": zaak["url"]})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    @requests_mock.Mocker()
    def test_read_logged_in_zaak_permission_atomic(self, m):
        user = UserFactory.create()
        self.client.force_authenticate(user)
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7",
        )
        m.get(zaak["url"], json=zaak)

        # set up user permissions
        AtomicPermissionFactory.create(
            for_user=user, permission=checklists_inzien.name, object_url=zaak["url"]
        )

        # set up test data
        ChecklistFactory.create(zaak="https://some-other-zaak-url.com")
        ChecklistFactory.create(zaak=zaak["url"])
        response = self.client.get(self.endpoint, {"zaak": zaak["url"]})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


class CreatePermissionTests(ClearCachesMixin, APITestCase):
    endpoint = reverse_lazy("checklist-list")

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        Service.objects.create(
            label="Zaken API", api_type=APITypes.zrc, api_root=ZAKEN_ROOT
        )
        Service.objects.create(
            label="Catalogi API",
            api_type=APITypes.ztc,
            api_root=CATALOGI_ROOT,
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
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7",
            zaaktype=cls.zaaktype["url"],
        )
        cls.checklist_type = ChecklistTypeFactory.create(
            zaaktype=cls.zaaktype["url"],
            zaaktype_omschrijving=cls.zaaktype["omschrijving"],
            zaaktype_catalogus=cls.zaaktype["catalogus"],
        )
        cls.checklist_question = ChecklistQuestionFactory.create(
            question="some-question",
            checklist_type=cls.checklist_type,
            order=1,
        )

    def setUp(self):
        super().setUp()
        self.user = UserFactory.create()

    def test_create_checklist_not_logged_in(self):
        response = self.client.post(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_create_checklist_logged_in_no_permissions(self, m):
        self.client.force_authenticate(user=self.user)
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(self.zaak["url"], json=self.zaak)
        m.get(self.zaaktype["url"], json=self.zaaktype)
        data = {
            "zaak": self.zaak["url"],
            "checklistType": self.checklist_type.uuid,
            "answers": [
                {"question": self.checklist_question.question, "answer": "some-answer"}
            ],
        }
        response = self.client.post(self.endpoint, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_create_checklist_logged_in_with_permissions_for_other_zaak(self, m):
        self.client.force_authenticate(user=self.user)
        BlueprintPermissionFactory.create(
            role__permissions=[checklists_schrijven.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus,
                "zaaktype_omschrijving": "ZT2",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(self.zaaktype["url"], json=self.zaaktype)
        m.get(self.zaak["url"], json=self.zaak)
        data = {
            "zaak": self.zaak["url"],
            "checklistType": self.checklist_type.uuid,
            "answers": [
                {"question": self.checklist_question.question, "answer": "some-answer"}
            ],
        }
        response = self.client.post(self.endpoint, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_create_checklist_logged_in_with_permissions(self, m):
        self.client.force_authenticate(user=self.user)
        BlueprintPermissionFactory.create(
            role__permissions=[checklists_schrijven.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )

        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(self.zaaktype["url"], json=self.zaaktype)
        m.get(self.zaak["url"], json=self.zaak)
        data = {
            "zaak": self.zaak["url"],
            "checklistType": self.checklist_type.uuid,
            "answers": [
                {"question": self.checklist_question.question, "answer": "some-answer"}
            ],
        }
        response = self.client.post(self.endpoint, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @requests_mock.Mocker()
    def test_create_checklist_logged_in_with_atomic_permissions(self, m):
        self.client.force_authenticate(user=self.user)
        AtomicPermissionFactory.create(
            permission=checklists_schrijven.name,
            for_user=self.user,
            object_url=self.zaak["url"],
        )

        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(self.zaaktype["url"], json=self.zaaktype)
        m.get(self.zaak["url"], json=self.zaak)
        data = {
            "zaak": self.zaak["url"],
            "checklistType": self.checklist_type.uuid,
            "answers": [
                {"question": self.checklist_question.question, "answer": "some-answer"}
            ],
        }
        response = self.client.post(self.endpoint, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class UpdatePermissionTests(ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        Service.objects.create(
            label="Zaken API", api_type=APITypes.zrc, api_root=ZAKEN_ROOT
        )
        Service.objects.create(
            label="Catalogi API",
            api_type=APITypes.ztc,
            api_root=CATALOGI_ROOT,
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
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7",
            zaaktype=cls.zaaktype["url"],
        )
        cls.checklist_type = ChecklistTypeFactory.create(
            zaaktype=cls.zaaktype["url"],
            zaaktype_omschrijving=cls.zaaktype["omschrijving"],
            zaaktype_catalogus=cls.zaaktype["catalogus"],
        )
        cls.checklist_question = ChecklistQuestionFactory.create(
            question="some-question",
            checklist_type=cls.checklist_type,
            order=1,
        )
        cls.checklist = ChecklistFactory.create(
            zaak=cls.zaak["url"],
            checklist_type=cls.checklist_type,
        )

    def setUp(self):
        super().setUp()
        self.user = UserFactory.create()

    def test_update_checklist_not_logged_in(self):
        endpoint = reverse("checklist-detail", kwargs={"pk": self.checklist.pk})
        response = self.client.patch(endpoint, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_update_checklist_logged_in_no_permission(self, m):
        endpoint = reverse("checklist-detail", kwargs={"pk": self.checklist.pk})
        self.client.force_authenticate(user=self.user)
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(self.zaaktype["url"], json=self.zaaktype)
        m.get(self.zaak["url"], json=self.zaak)
        data = {
            "checklistType": self.checklist_type.uuid,
            "zaak": self.zaak["url"],
            "answers": [
                {"question": self.checklist_question.question, "answer": "some-answer"}
            ],
        }
        response = self.client.put(endpoint, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_update_checklist_logged_in_with_permissions_for_other_zaak(self, m):
        endpoint = reverse("checklist-detail", kwargs={"pk": self.checklist.pk})
        self.client.force_authenticate(user=self.user)
        BlueprintPermissionFactory.create(
            role__permissions=[checklists_schrijven.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus,
                "zaaktype_omschrijving": "ZT2",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(self.zaaktype["url"], json=self.zaaktype)
        m.get(self.zaak["url"], json=self.zaak)
        data = {
            "checklistType": self.checklist_type.uuid,
            "zaak": self.zaak["url"],
            "answers": [
                {"question": self.checklist_question.question, "answer": "some-answer"}
            ],
        }
        response = self.client.put(endpoint, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_update_checklist_logged_in_with_permissions(self, m):
        endpoint = reverse("checklist-detail", kwargs={"pk": self.checklist.pk})
        self.client.force_authenticate(user=self.user)
        BlueprintPermissionFactory.create(
            role__permissions=[checklists_schrijven.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(self.zaaktype["url"], json=self.zaaktype)
        m.get(self.zaak["url"], json=self.zaak)
        data = {
            "checklistType": self.checklist_type.uuid,
            "zaak": self.zaak["url"],
            "answers": [
                {"question": self.checklist_question.question, "answer": "some-answer"}
            ],
        }
        response = self.client.put(endpoint, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @requests_mock.Mocker()
    def test_update_checklist_logged_in_with_atomic_permissions(self, m):
        endpoint = reverse("checklist-detail", kwargs={"pk": self.checklist.pk})
        self.client.force_authenticate(user=self.user)
        AtomicPermissionFactory.create(
            permission=checklists_schrijven.name,
            for_user=self.user,
            object_url=self.zaak["url"],
        )
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(self.zaaktype["url"], json=self.zaaktype)
        m.get(self.zaak["url"], json=self.zaak)
        data = {
            "checklistType": self.checklist_type.uuid,
            "zaak": self.zaak["url"],
            "answers": [
                {"question": self.checklist_question.question, "answer": "some-answer"}
            ],
        }
        response = self.client.put(endpoint, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
