from copy import deepcopy
from unittest.mock import patch

from django.urls import reverse_lazy

import requests_mock
from rest_framework.test import APITestCase
from zgw_consumers.models import APITypes, Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.constants import PermissionReason
from zac.accounts.models import AtomicPermission
from zac.accounts.tests.factories import GroupFactory, SuperUserFactory, UserFactory
from zac.core.models import CoreConfig, MetaObjectTypesConfig
from zac.core.permissions import zaken_inzien
from zac.core.tests.utils import ClearCachesMixin
from zac.elasticsearch.tests.utils import ESMixin
from zac.tests.utils import mock_resource_get, paginated_response

from ..permissions import checklists_inzien, checklists_schrijven
from .utils import (
    BRONORGANISATIE,
    CATALOGI_ROOT,
    CHECKLIST_OBJECT,
    CHECKLIST_OBJECTTYPE,
    CHECKLIST_OBJECTTYPE_LATEST_VERSION,
    CHECKLISTTYPE_OBJECT,
    CHECKLISTTYPE_OBJECTTYPE,
    IDENTIFICATIE,
    OBJECTS_ROOT,
    OBJECTTYPES_ROOT,
    ZAAK_URL,
    ZAKEN_ROOT,
)


@requests_mock.Mocker()
class GrantChecklistPermissionTests(ESMixin, ClearCachesMixin, APITestCase):
    endpoint = reverse_lazy(
        "zaak-checklist",
        kwargs={"bronorganisatie": BRONORGANISATIE, "identificatie": IDENTIFICATIE},
    )

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
        objects_service = Service.objects.create(
            api_type=APITypes.orc, api_root=OBJECTS_ROOT
        )
        objecttypes_service = Service.objects.create(
            api_type=APITypes.orc, api_root=OBJECTTYPES_ROOT
        )
        config = CoreConfig.get_solo()
        config.primary_objects_api = objects_service
        config.primary_objecttypes_api = objecttypes_service
        config.save()

        meta_config = MetaObjectTypesConfig.get_solo()
        meta_config.checklisttype_objecttype = CHECKLISTTYPE_OBJECTTYPE["url"]
        meta_config.checklist_objecttype = CHECKLIST_OBJECTTYPE["url"]
        meta_config.save()

        cls.catalogus = generate_oas_component(
            "ztc",
            "schemas/Catalogus",
            url=f"{CATALOGI_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd",
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
            url=f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7",
            zaaktype=cls.zaaktype["url"],
            bronorganisatie=BRONORGANISATIE,
            identificatie=IDENTIFICATIE,
        )
        cls.user = SuperUserFactory.create()
        cls.assignee = UserFactory.create()
        cls.group = GroupFactory.create()
        cls.assignee.groups.add(cls.group)

    def setUp(self):
        super().setUp()

        self.client.force_login(self.user)

    def test_create_checklist_without_assignee(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        mock_resource_get(m, self.zaak)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, CHECKLIST_OBJECTTYPE)
        mock_resource_get(m, CHECKLIST_OBJECTTYPE_LATEST_VERSION)
        m.get(f"{OBJECTTYPES_ROOT}objecttypes", json=[CHECKLIST_OBJECTTYPE])
        m.post(f"{OBJECTS_ROOT}objects", json=CHECKLIST_OBJECT, status_code=201)
        m.post(f"{ZAKEN_ROOT}zaakobjecten", json=[], status_code=201)
        data = {
            "answers": [
                {"question": "Ja?", "answer": ""},
                {
                    "question": "Nee?",
                    "answer": "",
                },
            ],
        }

        self.client.force_authenticate(user=self.user)

        with patch(
            "zac.contrib.objects.services.fetch_checklisttype_object",
            return_value=[CHECKLISTTYPE_OBJECT],
        ):
            with patch(
                "zac.contrib.objects.checklists.api.views.fetch_checklist_object",
                return_value=[],
            ):
                with patch(
                    "zac.contrib.objects.checklists.api.serializers.fetch_checklist",
                    return_value=None,
                ):
                    response = self.client.post(self.endpoint, data=data)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(AtomicPermission.objects.count(), 0)

    def test_create_checklist_with_assignee(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        mock_resource_get(m, self.zaak)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, CHECKLIST_OBJECTTYPE)
        mock_resource_get(m, CHECKLIST_OBJECTTYPE_LATEST_VERSION)
        m.get(f"{OBJECTTYPES_ROOT}objecttypes", json=[CHECKLIST_OBJECTTYPE])
        m.post(f"{ZAKEN_ROOT}zaakobjecten", json=[], status_code=201)
        data = {
            "answers": [
                {"question": "Ja?", "answer": ""},
                {
                    "question": "Nee?",
                    "answer": "",
                    "user_assignee": self.assignee.username,
                },
            ],
        }
        created = deepcopy(CHECKLIST_OBJECT)
        created["record"]["data"]["answers"] = data["answers"]
        m.post(f"{OBJECTS_ROOT}objects", json=created, status_code=201)

        self.assertEqual(AtomicPermission.objects.for_user(self.assignee).count(), 0)

        self.client.force_authenticate(user=self.user)
        with patch(
            "zac.contrib.objects.services.fetch_checklisttype_object",
            return_value=[CHECKLISTTYPE_OBJECT],
        ):
            with patch(
                "zac.contrib.objects.checklists.api.views.fetch_checklist_object",
                return_value=None,
            ):
                with patch(
                    "zac.contrib.objects.services.fetch_checklist_object",
                    return_value=None,
                ):
                    response = self.client.post(self.endpoint, data=data)

        self.assertEqual(response.status_code, 201)
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
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        mock_resource_get(m, self.zaak)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.catalogus)
        mock_resource_get(m, CHECKLIST_OBJECTTYPE)
        mock_resource_get(m, CHECKLIST_OBJECTTYPE_LATEST_VERSION)
        m.get(f"{OBJECTTYPES_ROOT}objecttypes", json=[CHECKLIST_OBJECTTYPE])
        m.post(f"{OBJECTS_ROOT}objects", json=CHECKLIST_OBJECT, status_code=201)
        m.post(f"{ZAKEN_ROOT}zaakobjecten", json=[], status_code=201)
        data = {
            "answers": [
                {"question": "Ja?", "answer": ""},
                {
                    "question": "Nee?",
                    "answer": "",
                    "group_assignee": self.group.name,
                },
            ],
        }

        self.assertEqual(AtomicPermission.objects.for_user(self.assignee).count(), 0)

        self.client.force_authenticate(user=self.user)
        with patch(
            "zac.contrib.objects.services.fetch_checklisttype_object",
            return_value=[CHECKLISTTYPE_OBJECT],
        ):
            with patch(
                "zac.contrib.objects.checklists.api.views.fetch_checklist_object",
                return_value=[],
            ):
                with patch(
                    "zac.contrib.objects.checklists.api.serializers.fetch_checklist",
                    return_value=None,
                ):
                    response = self.client.post(self.endpoint, data=data)

        self.assertEqual(response.status_code, 201)
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
        mock_service_oas_get(m, OBJECTS_ROOT, "objects")
        mock_service_oas_get(m, OBJECTTYPES_ROOT, "objecttypes")
        m.get(
            f"{ZAKEN_ROOT}zaken?bronorganisatie=123456789&identificatie=ZAAK-0000001",
            json=paginated_response([self.zaak]),
        )
        mock_resource_get(m, self.zaak)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.catalogus)

        data = {
            "answers": [
                {
                    "question": "Ja?",
                    "answer": "Ja",
                    "user_assignee": self.assignee.username,
                },
                {"question": "Nee?", "answer": ""},
            ],
        }
        json_response = deepcopy(CHECKLIST_OBJECT)
        json_response["record"]["data"]["answers"] = data["answers"]
        m.patch(
            f"{OBJECTS_ROOT}objects/{CHECKLIST_OBJECT['uuid']}",
            json=json_response,
            status_code=200,
        )

        self.assertEqual(AtomicPermission.objects.for_user(self.assignee).count(), 0)
        self.client.force_authenticate(user=self.user)

        with patch(
            "zac.contrib.objects.checklists.api.views.fetch_checklist_object",
            return_value=CHECKLIST_OBJECT,
        ):
            with patch(
                "zac.contrib.objects.services.fetch_checklisttype_object",
                return_value=[CHECKLISTTYPE_OBJECT],
            ):
                response = self.client.put(self.endpoint, data=data)

        self.assertEqual(response.status_code, 200)

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
