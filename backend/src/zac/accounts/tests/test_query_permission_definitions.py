from django.test import TestCase

from ..models import PermissionDefinition
from .factories import (
    AuthorizationProfileFactory,
    PermissionDefinitionFactory,
    UserFactory,
)


class PermissionDefinitionQueryTests(TestCase):
    def test_query_for_user(self):
        user = UserFactory.create()
        user_permission = PermissionDefinitionFactory.create()
        user.permission_definitions.add(user_permission)

        auth_profile_permission = PermissionDefinitionFactory.create()
        auth_profile = AuthorizationProfileFactory.create()
        auth_profile.permission_definitions.add(auth_profile_permission)
        user.auth_profiles.add(auth_profile)

        query_for_user = PermissionDefinition.objects.for_user(user)

        self.assertEqual(query_for_user.count(), 2)
        self.assertEqual(
            list(query_for_user.order_by("id")),
            [user_permission, auth_profile_permission],
        )

    def test_query_for_user_duplicated(self):
        permission = PermissionDefinitionFactory.create()

        user = UserFactory.create()
        user.permission_definitions.add(permission)

        auth_profile = AuthorizationProfileFactory.create()
        auth_profile.permission_definitions.add(permission)
        user.auth_profiles.add(auth_profile)

        query_for_user = PermissionDefinition.objects.for_user(user)

        self.assertEqual(query_for_user.count(), 1)
        self.assertEqual(query_for_user.get(), permission)
