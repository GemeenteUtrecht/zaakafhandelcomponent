from datetime import datetime

from django.urls import reverse_lazy
from django.utils.timezone import make_aware

from rest_framework import status
from rest_framework.test import APITestCase, APITransactionTestCase
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from zac.core.tests.utils import ClearCachesMixin
from zac.tests.mixins import FreezeTimeMixin

from ...constants import PermissionObjectTypeChoices
from ...models import UserAuthorizationProfile
from ...tests.factories import (
    AuthorizationProfileFactory,
    BlueprintPermissionFactory,
    RoleFactory,
    StaffUserFactory,
    SuperUserFactory,
    UserAuthProfileFactory,
    UserFactory,
)

CATALOGI_ROOT = "https://api.catalogi.nl/api/v1/"
CATALOGUS_URL = f"{CATALOGI_ROOT}catalogi/dfb14eb7-9731-4d22-95c2-dff4f33ef36d"


class UserAuthProfilePermissionsTests(APITestCase):
    url = reverse_lazy("userauthorizationprofile-list")

    def test_no_staff_user(self):
        user = UserFactory.create()
        self.client.force_authenticate(user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_user(self):
        user = StaffUserFactory.create()
        self.client.force_authenticate(user)

        response = self.client.get(self.url + f"?username={user}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_superuser(self):
        user = SuperUserFactory.create()
        self.client.force_authenticate(user)

        response = self.client.get(self.url + f"?username={user}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)


class UserAuthProfileAPITests(
    FreezeTimeMixin, ClearCachesMixin, APITransactionTestCase
):
    frozen_time = "1999-12-31T23:59:59Z"

    def setUp(self) -> None:
        super().setUp()

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)

        self.user = SuperUserFactory.create()
        self.client.force_authenticate(self.user)

    def test_list_user_auth_profiles_with_filters(self):
        role = RoleFactory.create()
        blueprint_permission = BlueprintPermissionFactory.create(
            role=role,
            object_type=PermissionObjectTypeChoices.zaak,
            policy={
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        auth_profile = AuthorizationProfileFactory.create()
        auth_profile.blueprint_permissions.add(blueprint_permission)

        userauthprofile = UserAuthProfileFactory.create(
            user=self.user, auth_profile=auth_profile
        )
        auth_profile2 = AuthorizationProfileFactory.create()
        auth_profile.blueprint_permissions.add(blueprint_permission)
        user2 = UserFactory.create()
        userauthprofile2 = UserAuthProfileFactory.create(
            user=user2, auth_profile=auth_profile2
        )
        userauthprofile3 = UserAuthProfileFactory.create(
            user=self.user, auth_profile=auth_profile2
        )
        url = reverse_lazy("userauthorizationprofile-list")

        with self.subTest("Username filter"):
            response = self.client.get(url + f"?username={self.user}")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                response.json(),
                {
                    "count": 2,
                    "next": None,
                    "previous": None,
                    "results": [
                        {
                            "id": userauthprofile.id,
                            "user": {
                                "id": self.user.id,
                                "username": self.user.username,
                                "firstName": self.user.first_name,
                                "fullName": self.user.get_full_name(),
                                "lastName": self.user.last_name,
                                "isStaff": self.user.is_staff,
                                "email": self.user.email,
                                "groups": [],
                            },
                            "authProfile": str(auth_profile.uuid),
                            "start": "1999-12-31T23:59:59Z",
                            "end": "2999-12-31T00:00:00Z",
                            "isActive": True,
                        },
                        {
                            "id": userauthprofile3.id,
                            "user": {
                                "id": self.user.id,
                                "username": self.user.username,
                                "firstName": self.user.first_name,
                                "fullName": self.user.get_full_name(),
                                "lastName": self.user.last_name,
                                "isStaff": self.user.is_staff,
                                "email": self.user.email,
                                "groups": [],
                            },
                            "authProfile": str(auth_profile2.uuid),
                            "start": "1999-12-31T23:59:59Z",
                            "end": "2999-12-31T00:00:00Z",
                            "isActive": True,
                        },
                    ],
                },
            )

        with self.subTest("Authprofile filter"):
            response = self.client.get(url + f"?auth_profile={auth_profile2.uuid}")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                response.json(),
                {
                    "count": 2,
                    "next": None,
                    "previous": None,
                    "results": [
                        {
                            "id": userauthprofile3.id,
                            "user": {
                                "id": self.user.id,
                                "username": self.user.username,
                                "firstName": self.user.first_name,
                                "fullName": self.user.get_full_name(),
                                "lastName": self.user.last_name,
                                "isStaff": self.user.is_staff,
                                "email": self.user.email,
                                "groups": [],
                            },
                            "authProfile": str(auth_profile2.uuid),
                            "start": "1999-12-31T23:59:59Z",
                            "end": "2999-12-31T00:00:00Z",
                            "isActive": True,
                        },
                        {
                            "id": userauthprofile2.id,
                            "user": {
                                "id": user2.id,
                                "username": user2.username,
                                "firstName": user2.first_name,
                                "fullName": user2.get_full_name(),
                                "lastName": user2.last_name,
                                "isStaff": user2.is_staff,
                                "email": user2.email,
                                "groups": [],
                            },
                            "authProfile": str(auth_profile2.uuid),
                            "start": "1999-12-31T23:59:59Z",
                            "end": "2999-12-31T00:00:00Z",
                            "isActive": True,
                        },
                    ],
                },
            )
        with self.subTest("Wrong filters"):
            response = self.client.get(url + f"?somebs=not-valid")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(
                [
                    {
                        "name": "_All__",
                        "code": "query-param-not-set",
                        "reason": "Please include one of the following query parameters: ['username', 'auth_profile', 'is_active']",
                    }
                ],
                response.json()["invalidParams"],
            )
        with self.subTest("Empty filters"):
            response = self.client.get(url + f"?username=")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(
                [
                    {
                        "name": "_All__",
                        "code": "query-param-non-empty",
                        "reason": "Please include a valid non-empty string for username.",
                    }
                ],
                response.json()["invalidParams"],
            )
        with self.subTest("Valid filter no user"):
            response = self.client.get(url + f"?username=this-user-does-not-exist")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(
                {
                    "count": 0,
                    "next": None,
                    "previous": None,
                    "results": [],
                },
                response.json(),
            )

    def test_retrieve_user_auth_profile(self):
        role = RoleFactory.create()
        blueprint_permission = BlueprintPermissionFactory.create(
            role=role,
            object_type=PermissionObjectTypeChoices.zaak,
            policy={
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        auth_profile = AuthorizationProfileFactory.create()
        auth_profile.blueprint_permissions.add(blueprint_permission)

        userauthprofile = UserAuthProfileFactory.create(
            user=self.user, auth_profile=auth_profile
        )
        url = reverse_lazy("userauthorizationprofile-detail", args=[userauthprofile.pk])

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "id": userauthprofile.id,
                "start": "1999-12-31T23:59:59Z",
                "end": "2999-12-31T00:00:00Z",
                "user": {
                    "id": self.user.id,
                    "username": self.user.username,
                    "firstName": self.user.first_name,
                    "fullName": self.user.get_full_name(),
                    "lastName": self.user.last_name,
                    "isStaff": self.user.is_staff,
                    "email": self.user.email,
                    "groups": [],
                },
                "authProfile": str(auth_profile.uuid),
                "isActive": True,
            },
        )

    def test_create_user_auth_profile(self):
        role = RoleFactory.create()
        blueprint_permission = BlueprintPermissionFactory.create(
            role=role,
            object_type=PermissionObjectTypeChoices.zaak,
            policy={
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        auth_profile = AuthorizationProfileFactory.create()
        auth_profile.blueprint_permissions.add(blueprint_permission)

        url = reverse_lazy("userauthorizationprofile-list")

        data = {
            "user": self.user.username,
            "authProfile": auth_profile.uuid,
            "start": "1999-12-31T23:59:59Z",
        }
        self.assertEqual(UserAuthorizationProfile.objects.count(), 0)
        response = self.client.post(url + f"?username={self.user}", data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(UserAuthorizationProfile.objects.count(), 1)
        userauthprofile = UserAuthorizationProfile.objects.get()
        self.assertEqual(
            response.json(),
            {
                "id": userauthprofile.id,
                "start": "1999-12-31T23:59:59Z",
                "end": "2999-12-31T00:00:00Z",
                "user": self.user.username,
                "authProfile": str(auth_profile.uuid),
                "isActive": True,
            },
        )

    def test_fail_create_user_auth_profile_duplicate(self):
        role = RoleFactory.create()
        blueprint_permission = BlueprintPermissionFactory.create(
            role=role,
            object_type=PermissionObjectTypeChoices.zaak,
            policy={
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        auth_profile = AuthorizationProfileFactory.create()
        auth_profile.blueprint_permissions.add(blueprint_permission)

        url = reverse_lazy("userauthorizationprofile-list")

        data = {
            "user": self.user.username,
            "authProfile": auth_profile.uuid,
        }
        self.assertEqual(UserAuthorizationProfile.objects.count(), 0)
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(UserAuthorizationProfile.objects.count(), 1)
        userauthprofile = UserAuthorizationProfile.objects.get()
        self.assertEqual(
            response.json(),
            {
                "id": userauthprofile.id,
                "start": "1999-12-31T23:59:59Z",
                "end": "2999-12-31T00:00:00Z",
                "user": self.user.username,
                "authProfile": str(auth_profile.uuid),
                "isActive": True,
            },
        )
        data = {
            "user": self.user.username,
            "authProfile": auth_profile.uuid,
            "start": "2000-12-31T23:59:59Z",
        }
        response = self.client.post(url, data)

        # Make sure it updated
        self.assertEqual(UserAuthorizationProfile.objects.count(), 2)
        # Make sure one is active and the other is deactivated
        self.assertEqual(
            UserAuthorizationProfile.objects.filter(is_active=True).count(), 1
        )
        uap2 = UserAuthorizationProfile.objects.filter(is_active=True).get()
        self.assertEqual(
            response.json(),
            {
                "authProfile": str(auth_profile.uuid),
                "end": "2999-12-31T00:00:00Z",
                "id": uap2.id,
                "start": "2000-12-31T23:59:59Z",
                "user": self.user.username,
                "isActive": True,
            },
        )

        # regression test for multiple uaps
        data = {
            "user": self.user.username,
            "authProfile": auth_profile.uuid,
            "start": "2001-01-01T23:59:59Z",
        }
        response = self.client.post(url, data)

        # Make sure it updated
        self.assertEqual(UserAuthorizationProfile.objects.count(), 3)
        # Make sure one is active and the other is deactivated
        self.assertEqual(
            UserAuthorizationProfile.objects.filter(is_active=True).count(), 1
        )
        uap3 = UserAuthorizationProfile.objects.filter(is_active=True).get()
        self.assertEqual(
            response.json(),
            {
                "authProfile": str(auth_profile.uuid),
                "end": "2999-12-31T00:00:00Z",
                "id": uap3.id,
                "start": "2001-01-01T23:59:59Z",
                "user": self.user.username,
                "isActive": True,
            },
        )

    def test_create_user_auth_profile_duplicate_but_different_time_period(self):
        role = RoleFactory.create()
        blueprint_permission = BlueprintPermissionFactory.create(
            role=role,
            object_type=PermissionObjectTypeChoices.zaak,
            policy={
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        auth_profile = AuthorizationProfileFactory.create()
        auth_profile.blueprint_permissions.add(blueprint_permission)

        # Make sure no user auth profiles exist yet
        self.assertEqual(UserAuthorizationProfile.objects.count(), 0)

        url = reverse_lazy("userauthorizationprofile-list")

        # Create one with start date: "1999-12-31T23:59:59Z"
        data = {
            "user": self.user.username,
            "authProfile": auth_profile.uuid,
            "start": "1999-12-31T23:59:59Z",
            "end": "2000-12-31T00:00:00Z",
        }
        response = self.client.post(url, data)

        # Make sure it's created...
        self.assertEqual(response.status_code, 201)
        self.assertEqual(UserAuthorizationProfile.objects.count(), 1)

        # ... according to expectations.
        userauthprofile = UserAuthorizationProfile.objects.get()
        self.assertEqual(
            response.json(),
            {
                "id": userauthprofile.id,
                "start": "1999-12-31T23:59:59Z",
                "end": "2000-12-31T00:00:00Z",
                "user": self.user.username,
                "authProfile": str(auth_profile.uuid),
                "isActive": True,
            },
        )

        # Make sure a "new" one gets created in a different time period and the other is deactivated
        data = {
            "user": self.user.username,
            "authProfile": auth_profile.uuid,
            "start": "2001-12-31T23:59:59Z",
        }
        response = self.client.post(url, data)

        # Check if success.
        self.assertEqual(UserAuthorizationProfile.objects.count(), 2)
        userauthprofile = UserAuthorizationProfile.objects.filter(
            start__exact=make_aware(datetime(2001, 12, 31, 23, 59, 59))
        ).get()

        # Success.
        self.assertEqual(
            response.json(),
            {
                "authProfile": str(auth_profile.uuid),
                "end": "2999-12-31T00:00:00Z",
                "id": userauthprofile.id,
                "start": "2001-12-31T23:59:59Z",
                "user": self.user.username,
                "isActive": True,
            },
        )

    def test_partially_update_user_auth_profile(self):
        role = RoleFactory.create()
        blueprint_permission = BlueprintPermissionFactory.create(
            role=role,
            object_type=PermissionObjectTypeChoices.zaak,
            policy={
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        auth_profile = AuthorizationProfileFactory.create()
        auth_profile.blueprint_permissions.add(blueprint_permission)

        userauthprofile = UserAuthProfileFactory.create(
            user=self.user, auth_profile=auth_profile
        )
        user2 = SuperUserFactory.create()
        data = {"user": user2.username}
        self.assertEqual(userauthprofile.user.username, self.user.username)
        url = reverse_lazy("userauthorizationprofile-detail", args=[userauthprofile.pk])

        self.assertEqual(UserAuthorizationProfile.objects.count(), 1)
        response = self.client.patch(url, data)
        self.assertEqual(UserAuthorizationProfile.objects.count(), 1)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "id": userauthprofile.id,
                "start": "1999-12-31T23:59:59Z",
                "end": "2999-12-31T00:00:00Z",
                "user": user2.username,
                "authProfile": str(auth_profile.uuid),
                "isActive": True,
            },
        )

    def test_update_user_auth_profile(self):
        role = RoleFactory.create()
        blueprint_permission = BlueprintPermissionFactory.create(
            role=role,
            object_type=PermissionObjectTypeChoices.zaak,
            policy={
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        auth_profile = AuthorizationProfileFactory.create()
        auth_profile.blueprint_permissions.add(blueprint_permission)

        userauthprofile = UserAuthProfileFactory.create(
            user=self.user, auth_profile=auth_profile
        )
        user2 = SuperUserFactory.create()
        data = {
            "user": user2.username,
            "start": "1999-12-31T23:59:59Z",
            "end": "2099-12-31T23:59:59Z",
            "authProfile": str(auth_profile.uuid),
        }
        self.assertEqual(userauthprofile.user.username, self.user.username)
        url = reverse_lazy("userauthorizationprofile-detail", args=[userauthprofile.pk])
        self.assertEqual(UserAuthorizationProfile.objects.count(), 1)
        response = self.client.put(url, data)
        self.assertEqual(UserAuthorizationProfile.objects.count(), 1)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "id": userauthprofile.id,
                "start": "1999-12-31T23:59:59Z",
                "end": "2099-12-31T23:59:59Z",
                "user": user2.username,
                "authProfile": str(auth_profile.uuid),
                "isActive": True,
            },
        )

    def test_delete_user_auth_profile(self):
        role = RoleFactory.create()
        blueprint_permission = BlueprintPermissionFactory.create(
            role=role,
            object_type=PermissionObjectTypeChoices.zaak,
            policy={
                "catalogus": "DOME",
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        auth_profile = AuthorizationProfileFactory.create()
        auth_profile.blueprint_permissions.add(blueprint_permission)

        userauthprofile = UserAuthProfileFactory.create(
            user=self.user, auth_profile=auth_profile
        )
        self.assertTrue(UserAuthorizationProfile.objects.exists())
        url = reverse_lazy("userauthorizationprofile-detail", args=[userauthprofile.pk])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(UserAuthorizationProfile.objects.exists())
