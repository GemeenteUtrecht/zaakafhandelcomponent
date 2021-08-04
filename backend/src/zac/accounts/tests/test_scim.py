from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase

from zac.accounts.models import AuthorizationProfile, User
from zac.accounts.tests.factories import (
    AuthorizationProfileFactory,
    BlueprintPermissionFactory,
    SuperUserFactory,
)


class AuthorizationProfileSCIMTests(APITestCase):
    def test_user_authenticated(self):
        response = self.client.get("/scim/v2/Groups")

        self.assertEqual(status.HTTP_401_UNAUTHORIZED, response.status_code)

    def test_get_auth_profile(self):
        user = SuperUserFactory.create(
            first_name="John", last_name="Doe", username="jdoe"
        )
        profile = AuthorizationProfileFactory.create(name="Test Auth Profile")
        user.auth_profiles.add(profile)
        user.save()

        self.client.force_login(user=user)
        response = self.client.get(f"/scim/v2/Groups/{profile.uuid}")

        self.assertEqual(status.HTTP_200_OK, response.status_code)

        actual_data = response.json()

        expected_data = {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
            "displayName": "Test Auth Profile",
            "id": str(profile.uuid),
            "meta": {
                "resourceType": "Group",
                "location": f"http://testserver/scim/v2/Groups/{profile.uuid}",
            },
            "members": [
                {
                    "value": str(user.id),
                    "$ref": f"http://testserver/scim/v2/Users/{user.id}",
                    "display": "John Doe",
                }
            ],
        }

        for key, value in expected_data.items():
            with self.subTest(key):
                self.assertEqual(value, actual_data[key])

    def test_add_members(self):
        user1 = SuperUserFactory.create()
        user2 = SuperUserFactory.create()
        profile = AuthorizationProfileFactory.create(name="Test Auth Profile")

        new_auth_data = {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "Operations": [
                {
                    "op": "add",
                    "path": "members",
                    "value": [
                        {
                            "display": user1.get_full_name(),
                            "$ref": f"https://testserver/scim/v2/Users/{user1.id}",
                            "value": str(user1.id),
                        },
                        {
                            "display": user2.get_full_name(),
                            "$ref": f"https://testserver/scim/v2/Users/{user2.id}",
                            "value": str(user2.id),
                        },
                    ],
                }
            ],
        }

        self.client.force_login(user=user1)
        response = self.client.patch(
            f"/scim/v2/Groups/{profile.uuid}", data=new_auth_data
        )

        self.assertEqual(status.HTTP_200_OK, response.status_code)

        self.assertEqual(1, user1.auth_profiles.count())
        self.assertEqual(profile, user1.auth_profiles.get())
        self.assertEqual(1, user2.auth_profiles.count())
        self.assertEqual(profile, user2.auth_profiles.get())

    def test_delete_member(self):
        user1 = SuperUserFactory.create()
        user2 = SuperUserFactory.create()
        profile = AuthorizationProfileFactory.create(name="Test Auth Profile")
        user2.auth_profiles.add(profile)
        user2.save()

        new_auth_data = {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "Operations": [
                {
                    "op": "remove",
                    "path": "members",
                    "value": [
                        {
                            "display": user2.get_full_name(),
                            "$ref": f"https://testserver/scim/v2/Users/{user2.id}",
                            "value": str(user2.id),
                        }
                    ],
                }
            ],
        }

        self.client.force_login(user=user1)
        response = self.client.patch(
            f"/scim/v2/Groups/{profile.uuid}", data=new_auth_data
        )

        self.assertEqual(status.HTTP_200_OK, response.status_code)

        user2.refresh_from_db()

        self.assertEqual(0, user2.auth_profiles.count())


class UserSCIMTests(APITestCase):
    def test_user_authenticated(self):

        response = self.client.get("/scim/v2/Users")

        self.assertEqual(status.HTTP_401_UNAUTHORIZED, response.status_code)

    @freeze_time("2021-08-04T09:26:22.746996+00:00")
    def test_get_a_user(self):
        user = SuperUserFactory.create(first_name="John", last_name="Doe")
        auth_profile = AuthorizationProfileFactory.create()
        user.auth_profiles.add(auth_profile)
        user.save()

        self.client.force_login(user=user)
        response = self.client.get(f"/scim/v2/Users/{user.id}")

        self.assertEqual(status.HTTP_200_OK, response.status_code)

        actual_data = response.json()

        expected_data = {
            "id": f"{user.id}",
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": f"{user.username}",
            "name": {"givenName": "John", "familyName": "Doe", "formatted": "John Doe"},
            "displayName": "John Doe",
            "emails": [{"value": f"{user.username}@zac", "primary": True}],
            "active": True,
            "groups": [
                {
                    "value": f"{auth_profile.uuid}",
                    "$ref": f"http://testserver/scim/v2/Groups/{auth_profile.uuid}",
                    "display": f"{auth_profile.name}",
                }
            ],
            "meta": {
                "resourceType": "User",
                "created": "2021-08-04T09:26:22.746996+00:00",
                "lastModified": "2021-08-04T09:26:22.746996+00:00",
                "location": f"http://testserver/scim/v2/Users/{user.id}",
            },
        }

        for key, value in expected_data.items():
            with self.subTest(key):
                self.assertEqual(value, actual_data[key])

    @freeze_time("2021-08-04T09:26:22.746996+00:00")
    def test_create_user(self):
        user = SuperUserFactory.create()

        new_user_data = {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": "ttoast",
            "name": {
                "givenName": "Test",
                "familyName": "Toast",
                "formatted": "Test Toast",
            },
            "displayName": "Test Toast",
            "emails": [{"value": "ttoast@zac.nl", "primary": True}],
            "password": "t3stPassword!",
            "active": True,
            "groups": [],
        }

        self.client.force_login(user=user)
        response = self.client.post("/scim/v2/Users", data=new_user_data)

        self.assertEqual(status.HTTP_201_CREATED, response.status_code)

        actual_data = response.json()

        new_user = User.objects.get(username="ttoast")
        expected_data = {
            "id": str(new_user.id),
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": "ttoast",
            "name": {
                "givenName": "Test",
                "familyName": "Toast",
                "formatted": "Test Toast",
            },
            "displayName": "Test Toast",
            "emails": [{"value": f"ttoast@zac.nl", "primary": True}],
            "active": True,
            "groups": [],
            "meta": {
                "resourceType": "User",
                "created": "2021-08-04T09:26:22.746996+00:00",
                "lastModified": "2021-08-04T09:26:22.746996+00:00",
                "location": f"http://testserver/scim/v2/Users/{new_user.id}",
            },
        }

        self.assertEqual(2, User.objects.all().count())

        for key, value in expected_data.items():
            with self.subTest(key):
                self.assertEqual(value, actual_data[key])

    def test_update_user(self):
        # Note: the update (PUT) is not meant to update the groups
        user = SuperUserFactory.create(first_name="John", last_name="Doe")

        new_user_data = {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "userName": f"{user.username}",
            "name": {
                "givenName": "John",
                "familyName": "DoeDoe",
                "formatted": "John DoeDoe",
            },
            "displayName": "John DoeDoe",
            "emails": [{"value": "j-doedoe@zac.nl", "primary": True}],
        }

        self.client.force_login(user=user)
        response = self.client.put(f"/scim/v2/Users/{user.id}", data=new_user_data)

        self.assertEqual(status.HTTP_200_OK, response.status_code)

        self.assertEqual(1, User.objects.all().count())
        user.refresh_from_db()

        self.assertEqual("DoeDoe", user.last_name)
        self.assertEqual("j-doedoe@zac.nl", user.email)

    def test_partial_update_user(self):
        user = SuperUserFactory.create(first_name="John", last_name="Doe")

        new_user_data = {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
            "Operations": [
                {"op": "replace", "path": "name.familyName", "value": "DoeDoe"}
            ],
        }

        self.client.force_login(user=user)
        response = self.client.patch(f"/scim/v2/Users/{user.id}", data=new_user_data)

        self.assertEqual(status.HTTP_200_OK, response.status_code)

        data = response.json()

        self.assertEqual("DoeDoe", data["name"]["familyName"])
        self.assertEqual("John DoeDoe", data["name"]["formatted"])
        self.assertEqual("John DoeDoe", data["displayName"])

        self.assertEqual(1, User.objects.all().count())
        user.refresh_from_db()

        self.assertEqual("DoeDoe", user.last_name)

    def test_remove_user(self):
        user1 = SuperUserFactory.create(first_name="John", last_name="Doe")
        user2 = SuperUserFactory.create(first_name="Jane", last_name="Doe")

        self.client.force_login(user=user2)
        response = self.client.delete(f"/scim/v2/Users/{user1.id}")

        self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code)
        self.assertEqual(1, User.objects.all().count())
