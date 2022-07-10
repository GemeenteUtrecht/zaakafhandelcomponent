from django.urls import reverse_lazy

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
from zac.core.permissions import zaken_geforceerd_bijwerken
from zac.core.tests.utils import ClearCachesMixin
from zac.elasticsearch.tests.utils import ESMixin
from zac.tests.utils import paginated_response

from ..permissions import checklists_inzien, checklists_schrijven
from .factories import ChecklistFactory, ChecklistQuestionFactory, ChecklistTypeFactory

ZAKEN_ROOT = "https://open-zaak.nl/zaken/api/v1/"
CATALOGI_ROOT = "https://open-zaak.nl/catalogi/api/v1/"
BRONORGANISATIE = "123456789"
IDENTIFICATIE = "ZAAK-0000001"


@requests_mock.Mocker()
class RetrieveChecklistsPermissionTests(ESMixin, ClearCachesMixin, APITestCase):
    """
    Test the checklist retrieve endpoint permissions.

    """

    endpoint = reverse_lazy(
        "zaak-checklist",
        kwargs={"bronorganisatie": BRONORGANISATIE, "identificatie": IDENTIFICATIE},
    )

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
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            catalogus=cls.catalogus,
            omschrijving="ZT1",
        )
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7",
            zaaktype=cls.zaaktype["url"],
            bronorganisatie=BRONORGANISATIE,
            identificatie=IDENTIFICATIE,
            einddatum="2020-01-01",
        )
        cls.user = UserFactory.create()

    def test_read_not_logged_in(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_read_logged_in_zaak_no_permission(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        m.get(self.zaaktype["url"], json=self.zaaktype)
        m.get(self.zaak["url"], json=self.zaak)

        ChecklistFactory.create(zaak=self.zaak["url"])

        self.client.force_authenticate(self.user)
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_read_logged_in_not_found(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        m.get(self.zaaktype["url"], json=self.zaaktype)
        BlueprintPermissionFactory.create(
            role__permissions=[checklists_inzien.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus,
                "zaaktype_omschrijving": self.zaaktype["omschrijving"],
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        self.client.force_authenticate(self.user)
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, 404)

    def test_read_logged_in_permissions_for_other_zaaktype(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        m.get(self.zaaktype["url"], json=self.zaaktype)
        m.get(self.zaak["url"], json=self.zaak)

        ChecklistFactory.create(zaak=self.zaak["url"])

        BlueprintPermissionFactory.create(
            role__permissions=[checklists_inzien.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus,
                "zaaktype_omschrijving": "ZT2",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        self.client.force_authenticate(self.user)
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_read_logged_in_zaak_permission_atomic(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        m.get(self.zaaktype["url"], json=self.zaaktype)
        m.get(self.zaak["url"], json=self.zaak)

        ChecklistFactory.create(zaak=self.zaak["url"])

        AtomicPermissionFactory.create(
            for_user=self.user,
            permission=checklists_inzien.name,
            object_url=self.zaak["url"],
        )
        self.client.force_authenticate(self.user)
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


@requests_mock.Mocker()
class CreateChecklistPermissionTests(ESMixin, ClearCachesMixin, APITestCase):
    endpoint = reverse_lazy(
        "zaak-checklist",
        kwargs={"bronorganisatie": BRONORGANISATIE, "identificatie": IDENTIFICATIE},
    )

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
            bronorganisatie=BRONORGANISATIE,
            identificatie=IDENTIFICATIE,
            einddatum=None,
        )
        cls.checklisttype = ChecklistTypeFactory.create(
            zaaktype=cls.zaaktype["url"],
            zaaktype_omschrijving=cls.zaaktype["omschrijving"],
            zaaktype_catalogus=cls.zaaktype["catalogus"],
        )
        cls.checklist_question = ChecklistQuestionFactory.create(
            question="some-question",
            checklisttype=cls.checklisttype,
            order=1,
        )
        cls.user = UserFactory.create()

    def test_create_checklist_not_logged_in(self, m):
        response = self.client.post(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_checklist_logged_in_no_permissions(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        m.get(self.zaaktype["url"], json=self.zaaktype)
        m.get(self.zaak["url"], json=self.zaak)
        data = {
            "answers": [
                {"question": self.checklist_question.question, "answer": "some-answer"}
            ],
        }
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.endpoint, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_checklist_logged_in_with_permissions_for_other_zaak(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        m.get(self.zaaktype["url"], json=self.zaaktype)
        m.get(self.zaak["url"], json=self.zaak)
        data = {
            "answers": [
                {"question": self.checklist_question.question, "answer": "some-answer"}
            ],
        }
        BlueprintPermissionFactory.create(
            role__permissions=[checklists_schrijven.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus,
                "zaaktype_omschrijving": "ZT2",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.endpoint, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_checklist_logged_in_with_permissions(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        m.get(self.zaaktype["url"], json=self.zaaktype)
        m.get(self.zaak["url"], json=self.zaak)
        data = {
            "answers": [
                {"question": self.checklist_question.question, "answer": "some-answer"}
            ],
        }
        BlueprintPermissionFactory.create(
            role__permissions=[checklists_schrijven.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus,
                "zaaktype_omschrijving": self.zaaktype["omschrijving"],
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.endpoint, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_checklist_logged_in_with_atomic_permissions(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        m.get(self.zaaktype["url"], json=self.zaaktype)
        m.get(self.zaak["url"], json=self.zaak)
        data = {
            "answers": [
                {"question": self.checklist_question.question, "answer": "some-answer"}
            ],
        }
        AtomicPermissionFactory.create(
            permission=checklists_schrijven.name,
            for_user=self.user,
            object_url=self.zaak["url"],
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.endpoint, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_checklist_logged_in_with_atomic_permissions_closed_zaak(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([{**self.zaak, "einddatum": "2020-01-01"}]),
        )
        m.get(self.zaaktype["url"], json=self.zaaktype)
        m.get(self.zaak["url"], json={**self.zaak, "einddatum": "2020-01-01"})
        data = {
            "answers": [
                {"question": self.checklist_question.question, "answer": "some-answer"}
            ],
        }
        AtomicPermissionFactory.create(
            permission=checklists_schrijven.name,
            for_user=self.user,
            object_url=self.zaak["url"],
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.endpoint, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_checklist_logged_in_with_both_atomic_permissions_closed_zaak(
        self, m
    ):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([{**self.zaak, "einddatum": "2020-01-01"}]),
        )
        m.get(self.zaaktype["url"], json=self.zaaktype)
        m.get(self.zaak["url"], json={**self.zaak, "einddatum": "2020-01-01"})
        data = {
            "answers": [
                {"question": self.checklist_question.question, "answer": "some-answer"}
            ],
        }
        AtomicPermissionFactory.create(
            permission=checklists_schrijven.name,
            for_user=self.user,
            object_url=self.zaak["url"],
        )
        AtomicPermissionFactory.create(
            permission=zaken_geforceerd_bijwerken.name,
            for_user=self.user,
            object_url=self.zaak["url"],
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.endpoint, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_checklist_logged_in_with_blueprint_permission_closed_zaak(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([{**self.zaak, "einddatum": "2020-01-01"}]),
        )
        m.get(self.zaaktype["url"], json=self.zaaktype)
        m.get(self.zaak["url"], json={**self.zaak, "einddatum": "2020-01-01"})
        data = {
            "answers": [
                {"question": self.checklist_question.question, "answer": "some-answer"}
            ],
        }
        BlueprintPermissionFactory.create(
            role__permissions=[checklists_schrijven.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus,
                "zaaktype_omschrijving": self.zaaktype["omschrijving"],
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.endpoint, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_checklist_logged_in_with_both_blueprint_permissions_closed_zaak(
        self, m
    ):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([{**self.zaak, "einddatum": "2020-01-01"}]),
        )
        m.get(self.zaaktype["url"], json=self.zaaktype)
        m.get(self.zaak["url"], json={**self.zaak, "einddatum": "2020-01-01"})
        data = {
            "answers": [
                {"question": self.checklist_question.question, "answer": "some-answer"}
            ],
        }
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_geforceerd_bijwerken.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus,
                "zaaktype_omschrijving": self.zaaktype["omschrijving"],
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        BlueprintPermissionFactory.create(
            role__permissions=[checklists_schrijven.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus,
                "zaaktype_omschrijving": self.zaaktype["omschrijving"],
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.endpoint, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


@requests_mock.Mocker()
class UpdatePermissionTests(ESMixin, ClearCachesMixin, APITestCase):
    endpoint = reverse_lazy(
        "zaak-checklist",
        kwargs={"bronorganisatie": BRONORGANISATIE, "identificatie": IDENTIFICATIE},
    )

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
            bronorganisatie=BRONORGANISATIE,
            identificatie=IDENTIFICATIE,
        )
        cls.checklisttype = ChecklistTypeFactory.create(
            zaaktype=cls.zaaktype["url"],
            zaaktype_omschrijving=cls.zaaktype["omschrijving"],
            zaaktype_catalogus=cls.zaaktype["catalogus"],
        )
        cls.checklist_question = ChecklistQuestionFactory.create(
            question="some-question",
            checklisttype=cls.checklisttype,
            order=1,
        )
        cls.checklist = ChecklistFactory.create(
            zaak=cls.zaak["url"],
            checklisttype=cls.checklisttype,
        )
        cls.user = UserFactory.create()

    def test_update_checklist_not_logged_in(self, m):
        response = self.client.patch(self.endpoint, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_checklist_logged_in_no_permission(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        m.get(self.zaaktype["url"], json=self.zaaktype)
        m.get(self.zaak["url"], json=self.zaak)

        data = {
            "answers": [
                {"question": self.checklist_question.question, "answer": "some-answer"}
            ],
        }
        self.client.force_authenticate(user=self.user)
        response = self.client.put(self.endpoint, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_checklist_logged_in_with_permissions_for_other_zaak(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        m.get(self.zaaktype["url"], json=self.zaaktype)
        m.get(self.zaak["url"], json=self.zaak)

        data = {
            "answers": [
                {"question": self.checklist_question.question, "answer": "some-answer"}
            ],
        }
        BlueprintPermissionFactory.create(
            role__permissions=[checklists_schrijven.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus,
                "zaaktype_omschrijving": "ZT2",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.put(self.endpoint, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_checklist_logged_in_with_permissions(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        m.get(self.zaaktype["url"], json=self.zaaktype)
        m.get(self.zaak["url"], json=self.zaak)

        data = {
            "answers": [
                {"question": self.checklist_question.question, "answer": "some-answer"}
            ],
        }
        BlueprintPermissionFactory.create(
            role__permissions=[checklists_schrijven.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.put(self.endpoint, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_checklist_logged_in_with_no_force_permission_closed_zaak(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([{**self.zaak, "einddatum": "2020-01-01"}]),
        )
        m.get(self.zaaktype["url"], json=self.zaaktype)
        m.get(self.zaak["url"], json={**self.zaak, "einddatum": "2020-01-01"})

        data = {
            "answers": [
                {"question": self.checklist_question.question, "answer": "some-answer"}
            ],
        }
        BlueprintPermissionFactory.create(
            role__permissions=[checklists_schrijven.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.put(self.endpoint, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_checklist_logged_in_with_no_force_permission_closed_zaak(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([{**self.zaak, "einddatum": "2020-01-01"}]),
        )
        m.get(self.zaaktype["url"], json=self.zaaktype)
        m.get(self.zaak["url"], json={**self.zaak, "einddatum": "2020-01-01"})

        data = {
            "answers": [
                {"question": self.checklist_question.question, "answer": "some-answer"}
            ],
        }
        BlueprintPermissionFactory.create(
            role__permissions=[checklists_schrijven.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_geforceerd_bijwerken.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.put(self.endpoint, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_checklist_logged_in_with_insufficient_atomic_permission_closed_zaak(
        self, m
    ):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([{**self.zaak, "einddatum": "2020-01-01"}]),
        )
        m.get(self.zaaktype["url"], json=self.zaaktype)
        m.get(self.zaak["url"], json={**self.zaak, "einddatum": "2020-01-01"})

        data = {
            "answers": [
                {"question": self.checklist_question.question, "answer": "some-answer"}
            ],
        }
        AtomicPermissionFactory.create(
            permission=checklists_schrijven.name,
            for_user=self.user,
            object_url=self.zaak["url"],
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.put(self.endpoint, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_checklist_logged_in_with_both_atomic_permissions(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        m.get(self.zaaktype["url"], json=self.zaaktype)
        m.get(self.zaak["url"], json=self.zaak)

        data = {
            "answers": [
                {"question": self.checklist_question.question, "answer": "some-answer"}
            ],
        }
        AtomicPermissionFactory.create(
            permission=checklists_schrijven.name,
            for_user=self.user,
            object_url=self.zaak["url"],
        )
        AtomicPermissionFactory.create(
            permission=zaken_geforceerd_bijwerken.name,
            for_user=self.user,
            object_url=self.zaak["url"],
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.put(self.endpoint, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
