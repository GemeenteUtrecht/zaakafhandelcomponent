from django.urls import reverse_lazy

from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase, APITransactionTestCase
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from zac.core.tests.utils import ClearCachesMixin

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

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_superuser(self):
        user = SuperUserFactory.create()
        self.client.force_authenticate(user)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)


@freeze_time("1999-12-31T23:59:59Z")
class UserAuthProfileAPITests(ClearCachesMixin, APITransactionTestCase):
    def setUp(self) -> None:
        super().setUp()

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)

        self.user = SuperUserFactory.create()
        self.client.force_authenticate(self.user)

    def test_list_user_auth_profiles(self):
        role = RoleFactory.create()
        blueprint_permission = BlueprintPermissionFactory.create(
            role=role,
            object_type=PermissionObjectTypeChoices.zaak,
            policy={
                "catalogus": CATALOGUS_URL,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        auth_profile = AuthorizationProfileFactory.create()
        auth_profile.blueprint_permissions.add(blueprint_permission)

        userauthprofile = UserAuthProfileFactory.create(
            user=self.user, auth_profile=auth_profile
        )
        url = reverse_lazy("userauthorizationprofile-list")

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "id": userauthprofile.id,
                        "start": "1999-12-31T23:59:59Z",
                        "end": None,
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
                    }
                ],
            },
        )

    def test_retrieve_user_auth_profile(self):
        role = RoleFactory.create()
        blueprint_permission = BlueprintPermissionFactory.create(
            role=role,
            object_type=PermissionObjectTypeChoices.zaak,
            policy={
                "catalogus": CATALOGUS_URL,
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
                "end": None,
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
            },
        )

    def test_create_user_auth_profile(self):
        role = RoleFactory.create()
        blueprint_permission = BlueprintPermissionFactory.create(
            role=role,
            object_type=PermissionObjectTypeChoices.zaak,
            policy={
                "catalogus": CATALOGUS_URL,
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
            "end": None,
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
                "end": None,
                "user": self.user.username,
                "authProfile": str(auth_profile.uuid),
            },
        )

    def test_partially_update_user_auth_profile(self):
        role = RoleFactory.create()
        blueprint_permission = BlueprintPermissionFactory.create(
            role=role,
            object_type=PermissionObjectTypeChoices.zaak,
            policy={
                "catalogus": CATALOGUS_URL,
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
                "end": None,
                "user": user2.username,
                "authProfile": str(auth_profile.uuid),
            },
        )

    def test_update_user_auth_profile(self):
        role = RoleFactory.create()
        blueprint_permission = BlueprintPermissionFactory.create(
            role=role,
            object_type=PermissionObjectTypeChoices.zaak,
            policy={
                "catalogus": CATALOGUS_URL,
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
            },
        )

    def test_delete_user_auth_profile(self):
        role = RoleFactory.create()
        blueprint_permission = BlueprintPermissionFactory.create(
            role=role,
            object_type=PermissionObjectTypeChoices.zaak,
            policy={
                "catalogus": CATALOGUS_URL,
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
