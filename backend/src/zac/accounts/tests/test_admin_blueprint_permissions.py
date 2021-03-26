import json
from dataclasses import dataclass
from typing import Optional, Type
from unittest.mock import patch

from django.urls import reverse_lazy

from django_webtest import WebTest
from rest_framework import serializers

from ..constants import PermissionObjectType
from ..models import BlueprintPermission
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


class BlueprintPermissionAdminTests(WebTest):
    url = reverse_lazy("admin:accounts_blueprintpermission_add")

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = SuperUserFactory.create()

    def setUp(self) -> None:
        super().setUp()

        self.app.set_user(self.user)

        patcher_registry_admin = patch("zac.accounts.admin.registry", new=test_registry)
        patcher_registry_model = patch(
            "zac.accounts.models.registry", new=test_registry
        )

        self.mocked_registry_admin = patcher_registry_admin.start()
        self.mocked_registry_model = patcher_registry_model.start()

        self.addCleanup(patcher_registry_admin.stop)
        self.addCleanup(patcher_registry_model.stop)

    def test_get_permission_choices(self):
        response = self.app.get(self.url)
        form = response.form

        permission_choices = form["permission"].options

        self.assertEqual(len(permission_choices), 2)
        self.assertEqual(
            [choice[0] for choice in permission_choices], ["", "permission1"]
        )

    def test_add_perm_definition_with_policy(self):
        get_response = self.app.get(self.url)

        form = get_response.form
        form["object_type"] = PermissionObjectType.zaak
        form["permission"] = "permission1"
        form["policy"] = json.dumps({"some_type": "new type"})

        response = form.submit()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(BlueprintPermission.objects.count(), 1)

        blueprint_permission = BlueprintPermission.objects.get()

        self.assertEqual(blueprint_permission.permission, "permission1")
        self.assertEqual(blueprint_permission.policy, {"some_type": "new type"})

    def test_add_perm_definition_with_policy_not_valid_for_blueprint(self):
        get_response = self.app.get(self.url)

        form = get_response.form
        form["object_type"] = PermissionObjectType.zaak
        form["permission"] = "permission1"
        form["policy"] = json.dumps({"some_type": "new type", "type_version": "v1"})

        response = form.submit()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(BlueprintPermission.objects.count(), 0)

        errors = response.context["errors"]

        self.assertEqual(
            str(errors[0].data[0].message), "type_version: Een geldig getal is vereist."
        )
