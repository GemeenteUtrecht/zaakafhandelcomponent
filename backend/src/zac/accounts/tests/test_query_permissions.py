from django.test import TestCase

from ..models import AtomicPermission, BlueprintPermission
from .factories import (
    AtomicPermissionFactory,
    AuthorizationProfileFactory,
    BlueprintPermissionFactory,
    UserFactory,
)


class AtomicPermissionQueryTests(TestCase):
    def test_query_for_user(self):
        user = UserFactory.create()
        user_permission = AtomicPermissionFactory.create()
        user.atomic_permissions.add(user_permission)

        query_for_user = AtomicPermission.objects.for_user(user)

        self.assertEqual(query_for_user.count(), 1)
        self.assertEqual(query_for_user.get(), user_permission)


class BlueprintPermissionQueryTests(TestCase):
    def test_query_for_user(self):
        user = UserFactory.create()
        auth_profile_permission = BlueprintPermissionFactory.create()
        auth_profile = AuthorizationProfileFactory.create()
        auth_profile.blueprint_permissions.add(auth_profile_permission)
        user.auth_profiles.add(auth_profile)

        query_for_user = BlueprintPermission.objects.for_user(user)

        self.assertEqual(query_for_user.count(), 1)
        self.assertEqual(query_for_user.get(), auth_profile_permission)

    def test_query_for_user_duplicated(self):
        permission = BlueprintPermissionFactory.create()

        user = UserFactory.create()
        # add two auth profiles for 1 user with the same atomic_permission
        auth_profiles = AuthorizationProfileFactory.create_batch(2)
        for auth_profile in auth_profiles:
            auth_profile.blueprint_permissions.add(permission)
            user.auth_profiles.add(auth_profile)

        query_for_user = BlueprintPermission.objects.for_user(user)

        self.assertEqual(query_for_user.count(), 1)
        self.assertEqual(query_for_user.get(), permission)
