import json
from dataclasses import dataclass
from typing import Optional, Type
from unittest.mock import patch

from django.urls import reverse_lazy

from django_webtest import WebTest
from rest_framework import serializers

from ..constants import PermissionObjectType
from ..models import PermissionDefinition
from ..permissions import Blueprint
from .factories import SuperUserFactory

test_registry = {}

# create a test permission in the separate registry
@dataclass(frozen=True)
class TestPermission:
    name: str
    description: str
    blueprint_class: Optional[Type[Blueprint]] = None

    def __post_init__(self):
        test_registry[self.name] = self


class TestBlueprint1(Blueprint):
    some_type = serializers.CharField(max_length=100)
    type_version = serializers.IntegerField(required=False)


permission1 = TestPermission(
    name="permission1", description="only for tests", blueprint_class=TestBlueprint1
)


class PermissionDefinitionAdminTests(WebTest):
    url = reverse_lazy("admin:accounts_permissiondefinition_add")

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = SuperUserFactory.create()

    def setUp(self) -> None:
        super().setUp()

        self.app.set_user(self.user)

        patcher_registry = patch("zac.accounts.admin.registry", new=test_registry)
        self.mocked_register_admin = patcher_registry.start()
        # local imports can't be patched without using sys.module, so we patch the whole method
        patcher_blueprint = patch(
            "zac.accounts.models.PermissionDefinition.get_blueprint_class",
            return_value=TestBlueprint1,
        )
        self.mocked_get_blueprint_class = patcher_blueprint.start()

        self.addCleanup(patcher_registry.stop)
        self.addCleanup(patcher_blueprint.stop)

    def test_get_permission_choices(self):
        response = self.app.get(self.url)
        form = response.form

        permission_choices = form["permission"].options

        self.assertEqual(len(permission_choices), 2)
        self.assertEqual(
            [choice[0] for choice in permission_choices], ["", "permission1"]
        )

    def test_add_perm_definition_with_object_url(self):
        get_response = self.app.get(self.url)

        form = get_response.form
        form["object_type"] = PermissionObjectType.zaak
        form["permission"] = "permission1"
        form["object_url"] = "http://zrc.nl/api/v1/zaken/some-zaak"

        response = form.submit()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(PermissionDefinition.objects.count(), 1)

        permission_definition = PermissionDefinition.objects.get()

        self.assertEqual(permission_definition.permission, "permission1")
        self.assertEqual(
            permission_definition.object_url, "http://zrc.nl/api/v1/zaken/some-zaak"
        )

    def test_add_perm_definition_with_policy(self):
        get_response = self.app.get(self.url)

        form = get_response.form
        form["object_type"] = PermissionObjectType.zaak
        form["permission"] = "permission1"
        form["policy"] = json.dumps({"some_type": "new type"})

        response = form.submit()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(PermissionDefinition.objects.count(), 1)

        permission_definition = PermissionDefinition.objects.get()

        self.assertEqual(permission_definition.permission, "permission1")
        self.assertEqual(permission_definition.policy, {"some_type": "new type"})

    def test_add_perm_definition_no_policy_no_object_url(self):
        get_response = self.app.get(self.url)

        form = get_response.form
        form["object_type"] = PermissionObjectType.zaak
        form["permission"] = "permission1"

        response = form.submit()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(PermissionDefinition.objects.count(), 0)

        errors = response.context["errors"]

        self.assertEqual(len(errors), 1)
        self.assertEqual(
            str(errors[0].data[0].message),
            "object_url and policy should be mutually exclusive",
        )

    def test_add_perm_definition_with_policy_not_valid_for_blueprint(self):
        get_response = self.app.get(self.url)

        form = get_response.form
        form["object_type"] = PermissionObjectType.zaak
        form["permission"] = "permission1"
        form["policy"] = json.dumps({"some_type": "new type", "type_version": "v1"})

        response = form.submit()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(PermissionDefinition.objects.count(), 0)

        errors = response.context["errors"]

        self.assertEqual(
            str(errors[0].data[0].message), "type_version: Een geldig getal is vereist."
        )
