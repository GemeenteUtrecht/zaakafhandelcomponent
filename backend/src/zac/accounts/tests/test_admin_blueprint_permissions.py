import json
from dataclasses import dataclass
from typing import Optional, Type
from unittest.mock import patch

from django.urls import reverse_lazy

from django_webtest import WebTest
from rest_framework import serializers

from ..constants import PermissionObjectTypeChoices
from ..models import BlueprintPermission
from ..permissions import Blueprint
from .factories import RoleFactory, SuperUserFactory

# create a test object type in the separate registry
test_object_type_registry = {}


@dataclass(frozen=True)
class TestObjectType:
    name: str
    blueprint_class: Optional[Type[Blueprint]] = None

    def __post_init__(self):
        test_object_type_registry[self.name] = self


class TestBlueprint1(Blueprint):
    some_type = serializers.CharField(max_length=100)
    type_version = serializers.IntegerField(required=False)


object_type1 = TestObjectType(
    name=PermissionObjectTypeChoices.zaak, blueprint_class=TestBlueprint1
)


class BlueprintPermissionAdminTests(WebTest):
    url = reverse_lazy("admin:accounts_blueprintpermission_add")

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = SuperUserFactory.create()
        cls.role = RoleFactory.create()

    def setUp(self) -> None:
        super().setUp()

        self.app.set_user(self.user)

        patcher_registry_widget = patch(
            "zac.accounts.widgets.object_type_registry", new=test_object_type_registry
        )
        patcher_registry_model = patch(
            "zac.accounts.models.object_type_registry", new=test_object_type_registry
        )

        self.mocked_registry_widget = patcher_registry_widget.start()
        self.mocked_registry_model = patcher_registry_model.start()

        self.addCleanup(patcher_registry_widget.stop)
        self.addCleanup(patcher_registry_model.stop)

    def test_add_perm_definition_with_policy(self):
        get_response = self.app.get(self.url)
        form = get_response.forms["blueprintpermission_form"]
        form["object_type"] = PermissionObjectTypeChoices.zaak
        form["role"] = self.role.id
        form["policy"] = json.dumps({"some_type": "new type"})

        response = form.submit()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(BlueprintPermission.objects.count(), 1)

        blueprint_permission = BlueprintPermission.objects.get()

        self.assertEqual(blueprint_permission.role, self.role)
        self.assertEqual(blueprint_permission.policy, {"some_type": "new type"})

    def test_add_perm_definition_with_policy_not_valid_for_blueprint(self):
        get_response = self.app.get(self.url)

        form = get_response.forms["blueprintpermission_form"]
        form["object_type"] = PermissionObjectTypeChoices.zaak
        form["role"] = self.role.id
        form["policy"] = json.dumps({"some_type": "new type", "type_version": "v1"})

        response = form.submit()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(BlueprintPermission.objects.count(), 0)

        errors = response.context["errors"]

        self.assertEqual(
            str(errors[0].data[0].message), "type_version: Een geldig getal is vereist."
        )
