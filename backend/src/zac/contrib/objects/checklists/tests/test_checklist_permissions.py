from copy import deepcopy
from unittest.mock import patch

from django.urls import reverse_lazy

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
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
from zac.tests.utils import mock_resource_get, paginated_response

from ..data import ChecklistType
from ..permissions import checklists_inzien, checklists_schrijven
from .utils import (
    BRONORGANISATIE,
    CATALOGI_ROOT,
    CHECKLIST_OBJECT,
    IDENTIFICATIE,
    OBJECTS_ROOT,
    OBJECTTYPES_ROOT,
    ZAAK_URL,
    ZAKEN_ROOT,
)


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
        cls.catalogus_url = (
            f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        )
        cls.catalogus = generate_oas_component(
            "ztc", "schemas/Catalogus", url=cls.catalogus_url, domein="some-domein"
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            catalogus=cls.catalogus_url,
            omschrijving="ZT1",
            identificatie="ZT1",
        )
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=ZAAK_URL,
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

        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.zaak)

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
        mock_resource_get(m, self.zaaktype)
        BlueprintPermissionFactory.create(
            role__permissions=[checklists_inzien.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus_url,
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
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.zaak)

        BlueprintPermissionFactory.create(
            role__permissions=[checklists_inzien.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus_url,
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
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.zaak)
        AtomicPermissionFactory.create(
            for_user=self.user,
            permission=checklists_inzien.name,
            object_url=self.zaak["url"],
        )
        self.client.force_authenticate(self.user)
        with patch(
            "zac.contrib.objects.checklists.api.views.fetch_checklist_object",
            return_value=CHECKLIST_OBJECT,
        ):
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
        cls.catalogus = generate_oas_component(
            "ztc",
            "schemas/Catalogus",
            url=f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd",
            domein="UTRE",
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            catalogus=cls.catalogus["url"],
            url=f"{CATALOGI_ROOT}zaaktypen/d66790b7-8b01-4005-a4ba-8fcf2a60f21d",
            identificatie="ZT1",
            omschrijving="ZT1",
        )
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=ZAAK_URL,
            zaaktype=cls.zaaktype["url"],
            bronorganisatie=BRONORGANISATIE,
            identificatie=IDENTIFICATIE,
            einddatum=None,
        )
        cls.user = UserFactory.create()

        cls.checklisttype = generate_oas_component(
            "checklists_objects",
            "schemas/ChecklistType",
            zaaktypeCatalogus=cls.catalogus["domein"],
            zaaktypeIdentificaties=[cls.zaaktype["identificatie"]],
            questions=[{"question": "some-question", "choices": [], "order": 1}],
            meta=True,
        )
        cls.checklisttype = factory(ChecklistType, cls.checklisttype)
        cls.patch_fetch_checklisttype = patch(
            "zac.contrib.objects.checklists.api.serializers.fetch_checklisttype",
            return_value=cls.checklisttype,
        )
        cls.patch_fetch_objecttype = patch(
            "zac.contrib.objects.checklists.api.serializers.fetch_objecttype",
            return_value={
                "versions": [
                    f"{OBJECTTYPES_ROOT}objecttypen/e13e72de-56ba-42b6-be36-5c280e9b30cf/version/1"
                ],
                "url": f"{OBJECTTYPES_ROOT}objecttypen/e13e72de-56ba-42b6-be36-5c280e9b30cf/version/1",
                "name": "some-name",
                "version": 1,
            },
        )
        cls.patch_fetch_checklist_object_views = patch(
            "zac.contrib.objects.checklists.api.views.fetch_checklist_object",
            return_value=None,
        )
        cls.patch_fetch_checklist = patch(
            "zac.contrib.objects.checklists.api.serializers.fetch_checklist",
            return_value=None,
        )

        cls.patch_create_object = patch(
            "zac.contrib.objects.checklists.api.serializers.create_object",
            return_value=CHECKLIST_OBJECT,
        )

        cls.patch_relate_object_to_zaak = patch(
            "zac.contrib.objects.checklists.api.serializers.relate_object_to_zaak",
            return_value=None,
        )

    def setUp(self):
        super().setUp()

        self.patch_fetch_checklisttype.start()
        self.addCleanup(self.patch_fetch_checklisttype.stop)

        self.patch_fetch_objecttype.start()
        self.addCleanup(self.patch_fetch_objecttype.stop)

        self.patch_fetch_checklist.start()
        self.addCleanup(self.patch_fetch_checklist.stop)

        self.patch_fetch_checklist_object_views.start()
        self.addCleanup(self.patch_fetch_checklist_object_views.stop)

        self.patch_create_object.start()
        self.addCleanup(self.patch_create_object.stop)

        self.patch_relate_object_to_zaak.start()
        self.addCleanup(self.patch_relate_object_to_zaak.stop)

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
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.zaak)
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.endpoint, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_checklist_logged_in_with_permissions_for_other_zaak(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.zaak)
        BlueprintPermissionFactory.create(
            role__permissions=[checklists_schrijven.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus["url"],
                "zaaktype_omschrijving": "ZT2",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.endpoint, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_checklist_logged_in_with_permissions(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.zaak)
        data = {
            "answers": [
                {
                    "question": self.checklisttype.questions[0].question,
                    "answer": "some-answer",
                }
            ],
        }
        BlueprintPermissionFactory.create(
            role__permissions=[checklists_schrijven.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus["url"],
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
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.zaak)
        data = {
            "answers": [
                {
                    "question": self.checklisttype.questions[0].question,
                    "answer": "some-answer",
                }
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
        mock_resource_get(m, self.zaaktype)
        m.get(self.zaak["url"], json={**self.zaak, "einddatum": "2020-01-01"})
        data = {
            "answers": [
                {
                    "question": self.checklisttype.questions[0].question,
                    "answer": "some-answer",
                }
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
        mock_resource_get(m, self.zaaktype)
        m.get(self.zaak["url"], json={**self.zaak, "einddatum": "2020-01-01"})
        data = {
            "answers": [
                {
                    "question": self.checklisttype.questions[0].question,
                    "answer": "some-answer",
                }
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
        mock_resource_get(m, self.zaaktype)
        m.get(self.zaak["url"], json={**self.zaak, "einddatum": "2020-01-01"})
        data = {
            "answers": [
                {
                    "question": self.checklisttype.questions[0].question,
                    "answer": "some-answer",
                }
            ],
        }
        BlueprintPermissionFactory.create(
            role__permissions=[checklists_schrijven.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus["url"],
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
        mock_resource_get(m, self.zaaktype)
        m.get(self.zaak["url"], json={**self.zaak, "einddatum": "2020-01-01"})
        data = {
            "answers": [
                {
                    "question": self.checklisttype.questions[0].question,
                    "answer": "some-answer",
                }
            ],
        }
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_geforceerd_bijwerken.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus["url"],
                "zaaktype_omschrijving": self.zaaktype["omschrijving"],
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        BlueprintPermissionFactory.create(
            role__permissions=[checklists_schrijven.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus["url"],
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
    lock_endpoint = reverse_lazy(
        "lock-zaak-checklist",
        kwargs={"bronorganisatie": BRONORGANISATIE, "identificatie": IDENTIFICATIE},
    )
    unlock_endpoint = reverse_lazy(
        "unlock-zaak-checklist",
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

        cls.catalogus = generate_oas_component(
            "ztc",
            "schemas/Catalogus",
            url=f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd",
            domein="UTRE",
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            catalogus=cls.catalogus["url"],
            url=f"{CATALOGI_ROOT}zaaktypen/d66790b7-8b01-4005-a4ba-8fcf2a60f21d",
            identificatie="ZT1",
            omschrijving="ZT1",
        )
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=ZAAK_URL,
            zaaktype=cls.zaaktype["url"],
            bronorganisatie=BRONORGANISATIE,
            identificatie=IDENTIFICATIE,
        )
        cls.user = UserFactory.create()

        cls.checklisttype = generate_oas_component(
            "checklists_objects",
            "schemas/ChecklistType",
            zaaktypeCatalogus=cls.catalogus["domein"],
            zaaktypeIdentificaties=[cls.zaaktype["identificatie"]],
            questions=[{"question": "some-question", "choices": [], "order": 1}],
            meta=True,
        )
        cls.checklisttype = factory(ChecklistType, cls.checklisttype)
        cls.patch_fetch_checklisttype = patch(
            "zac.contrib.objects.checklists.api.serializers.fetch_checklisttype",
            return_value=cls.checklisttype,
        )
        cls.patch_fetch_objecttype = patch(
            "zac.contrib.objects.checklists.api.serializers.fetch_objecttype",
            return_value={
                "versions": [
                    f"{OBJECTTYPES_ROOT}objecttypen/e13e72de-56ba-42b6-be36-5c280e9b30cf/version/1"
                ],
                "url": f"{OBJECTTYPES_ROOT}objecttypen/e13e72de-56ba-42b6-be36-5c280e9b30cf/version/1",
                "name": "some-name",
                "version": 1,
            },
        )
        data = deepcopy(CHECKLIST_OBJECT)
        data["record"]["data"]["lockedBy"] = cls.user.username
        cls.patch_fetch_checklist_object_views = patch(
            "zac.contrib.objects.checklists.api.views.fetch_checklist_object",
            return_value=data,
        )
        cls.patch_fetch_checklist_serializers = patch(
            "zac.contrib.objects.checklists.api.serializers.fetch_checklist",
            return_value=None,
        )

        data = deepcopy(data)
        data["record"]["data"]["zaak"] = cls.zaak["url"]
        cls.patch_update_object_record_data = patch(
            "zac.contrib.objects.checklists.api.serializers.update_object_record_data",
            return_value=data,
        )

    def setUp(self):
        super().setUp()

        self.patch_fetch_checklisttype.start()
        self.addCleanup(self.patch_fetch_checklisttype.stop)

        self.patch_fetch_objecttype.start()
        self.addCleanup(self.patch_fetch_objecttype.stop)

        self.patch_fetch_checklist_object_views.start()
        self.addCleanup(self.patch_fetch_checklist_object_views.stop)

        self.patch_fetch_checklist_serializers.start()
        self.addCleanup(self.patch_fetch_checklist_serializers.stop)

        self.patch_update_object_record_data.start()
        self.addCleanup(self.patch_update_object_record_data.stop)

    def test_update_checklist_not_logged_in(self, m):

        with self.subTest("PUT"):
            response = self.client.put(self.endpoint, {})
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        with self.subTest("POST LOCK"):
            response = self.client.post(self.lock_endpoint)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        with self.subTest("POST UNLOCK"):
            response = self.client.post(self.unlock_endpoint)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_checklist_logged_in_no_permission(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.zaak)

        self.client.force_authenticate(user=self.user)
        with self.subTest("PUT"):
            response = self.client.put(self.endpoint, {})
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        with self.subTest("POST LOCK"):
            response = self.client.post(self.lock_endpoint)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        with self.subTest("POST UNLOCK"):
            response = self.client.post(self.unlock_endpoint)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_checklist_logged_in_with_permissions_for_other_zaak(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.zaak)

        BlueprintPermissionFactory.create(
            role__permissions=[checklists_schrijven.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus["url"],
                "zaaktype_omschrijving": "ZT2",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.put(self.endpoint, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_checklist_logged_in_with_permissions(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.zaak)

        data = {
            "answers": [
                {
                    "question": self.checklisttype.questions[0].question,
                    "answer": "some-answer",
                }
            ],
        }
        BlueprintPermissionFactory.create(
            role__permissions=[checklists_schrijven.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus["url"],
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
        mock_resource_get(m, self.zaaktype)
        m.get(self.zaak["url"], json={**self.zaak, "einddatum": "2020-01-01"})

        data = {
            "answers": [
                {
                    "question": self.checklisttype.questions[0].question,
                    "answer": "some-answer",
                }
            ],
        }
        BlueprintPermissionFactory.create(
            role__permissions=[checklists_schrijven.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus["url"],
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
        mock_resource_get(m, self.zaaktype)
        m.get(self.zaak["url"], json={**self.zaak, "einddatum": "2020-01-01"})

        data = {
            "answers": [
                {
                    "question": self.checklisttype.questions[0].question,
                    "answer": "some-answer",
                }
            ],
        }
        BlueprintPermissionFactory.create(
            role__permissions=[checklists_schrijven.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus["url"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_geforceerd_bijwerken.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus["url"],
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
        mock_resource_get(m, self.zaaktype)
        m.get(self.zaak["url"], json={**self.zaak, "einddatum": "2020-01-01"})

        data = {
            "answers": [
                {
                    "question": self.checklisttype.questions[0].question,
                    "answer": "some-answer",
                }
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

    def test_update_checklist_logged_in_with_both_atomic_permissions_and_locked_by_updater(
        self, m
    ):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.zaak)

        data = {
            "answers": [
                {
                    "question": self.checklisttype.questions[0].question,
                    "answer": "some-answer",
                }
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

    def test_update_checklist_logged_in_with_both_atomic_permissions_but_not_locked(
        self, m
    ):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.zaak)

        data = {
            "answers": [
                {
                    "question": self.checklisttype.questions[0].question,
                    "answer": "some-answer",
                }
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
        data = deepcopy(CHECKLIST_OBJECT)
        data["record"]["data"]["lockedBy"] = None
        with patch(
            "zac.contrib.objects.checklists.api.views.fetch_checklist_object",
            return_value=data,
        ):
            response = self.client.put(self.endpoint, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_checklist_logged_in_with_both_atomic_permissions_but_checklist_is_locked(
        self, m
    ):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.zaak)

        data = {
            "answers": [
                {
                    "question": self.checklisttype.questions[0].question,
                    "answer": "some-answer",
                }
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
        # create some-other-user
        user = UserFactory.create(username="some-other-user")
        checklist_object = deepcopy(CHECKLIST_OBJECT)
        checklist_object["record"]["data"]["lockedBy"] = "some-other-user"

        with patch(
            "zac.contrib.objects.checklists.api.views.fetch_checklist_object",
            return_value=checklist_object,
        ):
            response = self.client.put(self.endpoint, data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.json(),
            {"detail": f"Checklist is currently locked by `some-other-user`."},
        )


@requests_mock.Mocker()
class LockAndUnlockChecklistPermissionTests(ESMixin, ClearCachesMixin, APITestCase):
    lock_endpoint = reverse_lazy(
        "lock-zaak-checklist",
        kwargs={"bronorganisatie": BRONORGANISATIE, "identificatie": IDENTIFICATIE},
    )
    unlock_endpoint = reverse_lazy(
        "unlock-zaak-checklist",
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

        cls.catalogus = generate_oas_component(
            "ztc",
            "schemas/Catalogus",
            url=f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd",
            domein="UTRE",
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            catalogus=cls.catalogus["url"],
            url=f"{CATALOGI_ROOT}zaaktypen/d66790b7-8b01-4005-a4ba-8fcf2a60f21d",
            identificatie="ZT1",
            omschrijving="ZT1",
        )
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=ZAAK_URL,
            zaaktype=cls.zaaktype["url"],
            bronorganisatie=BRONORGANISATIE,
            identificatie=IDENTIFICATIE,
        )
        cls.user = UserFactory.create()
        data = deepcopy(CHECKLIST_OBJECT)
        data["record"]["data"]["zaak"] = cls.zaak["url"]
        cls.patch_update_object_record_data = patch(
            "zac.contrib.objects.checklists.api.views.update_object_record_data",
            return_value=None,
        )
        cls.lock_checklist_object = deepcopy(CHECKLIST_OBJECT)
        cls.unlock_checklist_object = deepcopy(CHECKLIST_OBJECT)
        cls.unlock_checklist_object["record"]["data"]["lockedBy"] = cls.user.username

    def setUp(self):
        super().setUp()
        self.patch_update_object_record_data.start()
        self.addCleanup(self.patch_update_object_record_data.stop)

    def test_un_lock_checklist_not_logged_in(self, m):
        with self.subTest("LOCK"):
            with patch(
                "zac.contrib.objects.checklists.api.views.fetch_checklist_object",
                return_value=self.lock_checklist_object,
            ):
                response = self.client.post(self.lock_endpoint)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        with self.subTest("UNLOCK"):
            with patch(
                "zac.contrib.objects.checklists.api.views.fetch_checklist_object",
                return_value=self.unlock_checklist_object,
            ):
                response = self.client.post(self.unlock_endpoint)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_un_lock_checklist_logged_in_no_permission(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.zaak)

        self.client.force_authenticate(user=self.user)

        with self.subTest("LOCK"):
            with patch(
                "zac.contrib.objects.checklists.api.views.fetch_checklist_object",
                return_value=self.lock_checklist_object,
            ):
                response = self.client.post(self.lock_endpoint)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        with self.subTest("UNLOCK"):
            with patch(
                "zac.contrib.objects.checklists.api.views.fetch_checklist_object",
                return_value=self.unlock_checklist_object,
            ):
                response = self.client.post(self.unlock_endpoint)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_un_lock_checklist_logged_in_with_permissions_for_other_zaak(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.zaak)

        BlueprintPermissionFactory.create(
            role__permissions=[checklists_schrijven.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus["url"],
                "zaaktype_omschrijving": "ZT2",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        self.client.force_authenticate(user=self.user)

        with self.subTest("LOCK"):
            with patch(
                "zac.contrib.objects.checklists.api.views.fetch_checklist_object",
                return_value=self.lock_checklist_object,
            ):
                response = self.client.post(self.lock_endpoint)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        with self.subTest("UNLOCK"):
            with patch(
                "zac.contrib.objects.checklists.api.views.fetch_checklist_object",
                return_value=self.unlock_checklist_object,
            ):
                response = self.client.post(self.unlock_endpoint)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_un_lock_checklist_logged_in_with_permissions(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.zaak)

        BlueprintPermissionFactory.create(
            role__permissions=[checklists_schrijven.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus["url"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        self.client.force_authenticate(user=self.user)
        with self.subTest("LOCK"):
            with patch(
                "zac.contrib.objects.checklists.api.views.fetch_checklist_object",
                return_value=self.lock_checklist_object,
            ):
                response = self.client.post(self.lock_endpoint)
                self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        with self.subTest("UNLOCK"):
            with patch(
                "zac.contrib.objects.checklists.api.views.fetch_checklist_object",
                return_value=self.unlock_checklist_object,
            ):
                response = self.client.post(self.unlock_endpoint)
                self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_un_lock_checklist_logged_in_with_no_force_permission_closed_zaak(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([{**self.zaak, "einddatum": "2020-01-01"}]),
        )
        mock_resource_get(m, self.zaaktype)
        m.get(self.zaak["url"], json={**self.zaak, "einddatum": "2020-01-01"})
        BlueprintPermissionFactory.create(
            role__permissions=[checklists_schrijven.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus["url"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        self.client.force_authenticate(user=self.user)
        with self.subTest("LOCK"):
            with patch(
                "zac.contrib.objects.checklists.api.views.fetch_checklist_object",
                return_value=self.lock_checklist_object,
            ):
                response = self.client.post(self.lock_endpoint)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        with self.subTest("UNLOCK"):
            with patch(
                "zac.contrib.objects.checklists.api.views.fetch_checklist_object",
                return_value=self.unlock_checklist_object,
            ):
                response = self.client.post(self.unlock_endpoint)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_un_lock_checklist_logged_in_with_force_permission_closed_zaak(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([{**self.zaak, "einddatum": "2020-01-01"}]),
        )
        mock_resource_get(m, self.zaaktype)
        m.get(self.zaak["url"], json={**self.zaak, "einddatum": "2020-01-01"})

        BlueprintPermissionFactory.create(
            role__permissions=[checklists_schrijven.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus["url"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_geforceerd_bijwerken.name],
            for_user=self.user,
            policy={
                "catalogus": self.catalogus["url"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        self.client.force_authenticate(user=self.user)
        with self.subTest("LOCK"):
            with patch(
                "zac.contrib.objects.checklists.api.views.fetch_checklist_object",
                return_value=self.lock_checklist_object,
            ):
                response = self.client.post(self.lock_endpoint)
                self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        with self.subTest("UNLOCK"):
            with patch(
                "zac.contrib.objects.checklists.api.views.fetch_checklist_object",
                return_value=self.unlock_checklist_object,
            ):
                response = self.client.post(self.unlock_endpoint)
                self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_un_lock_checklist_logged_in_with_insufficient_atomic_permission_closed_zaak(
        self, m
    ):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([{**self.zaak, "einddatum": "2020-01-01"}]),
        )
        mock_resource_get(m, self.zaaktype)
        m.get(self.zaak["url"], json={**self.zaak, "einddatum": "2020-01-01"})
        AtomicPermissionFactory.create(
            permission=checklists_schrijven.name,
            for_user=self.user,
            object_url=self.zaak["url"],
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.lock_endpoint)
        with self.subTest("LOCK"):
            with patch(
                "zac.contrib.objects.checklists.api.views.fetch_checklist_object",
                return_value=self.lock_checklist_object,
            ):
                response = self.client.post(self.lock_endpoint)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        with self.subTest("UNLOCK"):
            with patch(
                "zac.contrib.objects.checklists.api.views.fetch_checklist_object",
                return_value=self.unlock_checklist_object,
            ):
                response = self.client.post(self.unlock_endpoint)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_un_lock_checklist_logged_in_with_both_atomic_permissions(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.zaak)
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
        response = self.client.post(self.lock_endpoint)
        with self.subTest("LOCK"):
            with patch(
                "zac.contrib.objects.checklists.api.views.fetch_checklist_object",
                return_value=self.lock_checklist_object,
            ):
                response = self.client.post(self.lock_endpoint)
                self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        with self.subTest("UNLOCK"):
            with patch(
                "zac.contrib.objects.checklists.api.views.fetch_checklist_object",
                return_value=self.unlock_checklist_object,
            ):
                response = self.client.post(self.unlock_endpoint)
                self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_un_lock_checklist_logged_in_with_permissions_but_checklist_is_already_locked_by_someone_else(
        self, m
    ):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.zaak)

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
        # create some-other-user
        user = UserFactory.create(username="some-other-user")
        checklist_object = deepcopy(CHECKLIST_OBJECT)
        checklist_object["record"]["data"]["lockedBy"] = "some-other-user"

        with patch(
            "zac.contrib.objects.checklists.api.views.fetch_checklist_object",
            return_value=checklist_object,
        ):
            with self.subTest("LOCK"):
                response = self.client.post(self.lock_endpoint)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
                self.assertEqual(
                    response.json(),
                    {"detail": f"Checklist is currently locked by `some-other-user`."},
                )

            with self.subTest("UNLOCK"):
                response = self.client.post(self.unlock_endpoint)
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
                self.assertEqual(
                    response.json(),
                    {"detail": f"Checklist is currently locked by `some-other-user`."},
                )
