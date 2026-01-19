from copy import deepcopy
from unittest.mock import patch

from django.urls import reverse_lazy

import requests_mock
from rest_framework.test import APITestCase
from zgw_consumers.constants import APITypes

from zac.accounts.constants import PermissionReason
from zac.accounts.models import AtomicPermission
from zac.accounts.tests.factories import GroupFactory, SuperUserFactory, UserFactory
from zac.core.models import CoreConfig, MetaObjectTypesConfig
from zac.core.permissions import zaken_inzien
from zac.core.tests.utils import ClearCachesMixin
from zac.elasticsearch.tests.utils import ESMixin
from zac.tests import ServiceFactory
from zac.tests.compat import generate_oas_component, mock_service_oas_get
from zac.tests.utils import mock_resource_get, paginated_response

from ..permissions import checklists_inzien, checklists_schrijven
from .factories import (
    BRONORGANISATIE,
    CATALOGI_ROOT,
    IDENTIFICATIE,
    OBJECTS_ROOT,
    OBJECTTYPES_ROOT,
    ZAAK_URL,
    ZAKEN_ROOT,
    checklist_object_factory,
    checklist_object_type_factory,
    checklist_object_type_version_factory,
    checklist_type_object_factory,
    checklist_type_object_type_version_factory,
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
        ServiceFactory.create(
            label="Catalogi API",
            api_type=APITypes.ztc,
            api_root=CATALOGI_ROOT,
        )
        ServiceFactory.create(
            label="Zaken API", api_type=APITypes.zrc, api_root=ZAKEN_ROOT
        )
        objects_service = ServiceFactory.create(
            api_type=APITypes.orc, api_root=OBJECTS_ROOT
        )
        objecttypes_service = ServiceFactory.create(
            api_type=APITypes.orc, api_root=OBJECTTYPES_ROOT
        )
        config = CoreConfig.get_solo()
        config.primary_objects_api = objects_service
        config.primary_objecttypes_api = objecttypes_service
        config.save()

        cls.checklisttype_objecttype = checklist_type_object_type_version_factory()
        cls.checklist_objecttype = checklist_object_type_factory()

        meta_config = MetaObjectTypesConfig.get_solo()
        meta_config.checklisttype_objecttype = cls.checklisttype_objecttype["url"]
        meta_config.checklist_objecttype = cls.checklist_objecttype["url"]
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
        cls.checklist_objecttype = checklist_object_type_factory()
        cls.checklist_objecttype_version = checklist_object_type_version_factory()
        cls.checklist_object = checklist_object_factory()
        cls.checklisttype_object = checklist_type_object_factory()

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
        mock_resource_get(m, self.checklist_objecttype)
        mock_resource_get(m, self.checklist_objecttype_version)
        m.get(
            f"{OBJECTTYPES_ROOT}objecttypes",
            json=paginated_response([self.checklist_objecttype]),
        )
        m.post(f"{OBJECTS_ROOT}objects", json=self.checklist_object, status_code=201)
        m.post(f"{ZAKEN_ROOT}zaakobjecten", json=[], status_code=201)
        data = {
            "answers": [
                {"question": "Ja?", "answer": "Ja"},
                {
                    "question": "Nee?",
                    "answer": "Nee",
                },
            ],
        }

        self.client.force_authenticate(user=self.user)

        with patch(
            "zac.contrib.objects.services.fetch_checklisttype_object",
            return_value=[self.checklisttype_object],
        ):
            with patch(
                "zac.contrib.objects.checklists.api.views.fetch_checklist_object",
                return_value=self.checklist_object,
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
        mock_resource_get(m, self.checklist_objecttype)
        mock_resource_get(m, self.checklist_objecttype_version)
        m.get(
            f"{OBJECTTYPES_ROOT}objecttypes",
            json=paginated_response([self.checklist_objecttype]),
        )
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
        created = deepcopy(self.checklist_object)
        created["record"]["data"]["answers"] = data["answers"]
        m.post(f"{OBJECTS_ROOT}objects", json=created, status_code=201)

        self.assertEqual(AtomicPermission.objects.for_user(self.assignee).count(), 0)

        self.client.force_authenticate(user=self.user)
        with patch(
            "zac.contrib.objects.services.fetch_checklisttype_object",
            return_value=[self.checklisttype_object],
        ):
            with patch(
                "zac.contrib.objects.checklists.api.views.fetch_checklist_object",
                return_value=created,
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
        mock_resource_get(m, self.checklist_objecttype)
        mock_resource_get(m, self.checklist_objecttype_version)
        m.get(
            f"{OBJECTTYPES_ROOT}objecttypes",
            json=paginated_response([self.checklist_objecttype]),
        )
        m.post(f"{OBJECTS_ROOT}objects", json=self.checklist_object, status_code=201)
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
        created = checklist_object_factory(record__data__answers=data["answers"])

        self.assertEqual(AtomicPermission.objects.for_user(self.assignee).count(), 0)

        self.client.force_authenticate(user=self.user)
        with patch(
            "zac.contrib.objects.services.fetch_checklisttype_object",
            return_value=[self.checklisttype_object],
        ):
            with patch(
                "zac.contrib.objects.checklists.api.views.fetch_checklist_object",
                return_value=created,
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
        json_response = checklist_object_factory(record__data__answers=data["answers"])
        m.patch(
            f"{OBJECTS_ROOT}objects/{self.checklist_object['uuid']}",
            json=json_response,
            status_code=200,
        )

        self.assertEqual(AtomicPermission.objects.for_user(self.assignee).count(), 0)
        self.client.force_authenticate(user=self.user)

        with patch(
            "zac.contrib.objects.checklists.api.views.fetch_checklist_object",
            side_effect=[self.checklist_object, json_response],
        ):
            with patch(
                "zac.contrib.objects.services.fetch_checklisttype_object",
                return_value=[self.checklisttype_object],
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
