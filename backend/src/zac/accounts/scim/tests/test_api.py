# from django.contrib.auth.models import Permission

# from freezegun import freeze_time
# from rest_framework import status
# from rest_framework.authtoken.models import Token
# from rest_framework.test import APITestCase

# from ...models import User
# from ...tests.factories import (
#     AuthorizationProfileFactory,
#     SuperUserFactory,
#     UserFactory,
# )


# class AuthorizationProfileSCIMTests(APITestCase):
#     @classmethod
#     def setUpTestData(cls):
#         super().setUpTestData()

#         cls.user = UserFactory.create()
#         cls.token = Token.objects.create(user=cls.user)
#         permission = Permission.objects.get(
#             codename="use_scim", content_type__app_label="accounts"
#         )
#         cls.user.user_permissions.add(permission)

#     def test_user_authenticated(self):
#         response = self.client.get("/scim/v2/Groups")

#         self.assertEqual(status.HTTP_401_UNAUTHORIZED, response.status_code)

#     def test_token_auth(self):
#         response = self.client.get(
#             "/scim/v2/Groups", HTTP_AUTHORIZATION=f"Token {self.token.key}"
#         )

#         self.assertEqual(status.HTTP_200_OK, response.status_code)

#     def test_token_auth_without_required_permission(self):
#         user = UserFactory.create()
#         token = Token.objects.create(user=user)

#         response = self.client.get(
#             "/scim/v2/Groups", HTTP_AUTHORIZATION=f"Token {token.key}"
#         )

#         self.assertEqual(status.HTTP_403_FORBIDDEN, response.status_code)

#     def test_get_auth_profile(self):
#         user = SuperUserFactory.create(
#             first_name="John", last_name="Doe", username="jdoe"
#         )
#         profile = AuthorizationProfileFactory.create(name="Test Auth Profile")
#         user.auth_profiles.add(profile)
#         user.save()

#         self.client.force_login(user=user)
#         response = self.client.get(f"/scim/v2/Groups/{profile.uuid}")

#         self.assertEqual(status.HTTP_200_OK, response.status_code)

#         actual_data = response.json()

#         expected_data = {
#             "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
#             "displayName": "Test Auth Profile",
#             "id": str(profile.uuid),
#             "meta": {
#                 "resourceType": "Group",
#                 "location": f"http://testserver/scim/v2/Groups/{profile.uuid}",
#             },
#             "members": [
#                 {
#                     "value": str(user.uuid),
#                     "$ref": f"http://testserver/scim/v2/Users/{user.uuid}",
#                     "display": "John Doe",
#                 }
#             ],
#         }

#         for key, value in expected_data.items():
#             with self.subTest(key):
#                 self.assertEqual(value, actual_data[key])

#     def test_add_members(self):
#         user1 = SuperUserFactory.create()
#         user2 = SuperUserFactory.create()
#         profile = AuthorizationProfileFactory.create(name="Test Auth Profile")

#         new_auth_data = {
#             "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
#             "Operations": [
#                 {
#                     "op": "add",
#                     "path": "members",
#                     "value": [
#                         {
#                             "display": user1.get_full_name(),
#                             "$ref": f"https://testserver/scim/v2/Users/{user1.uuid}",
#                             "value": str(user1.id),
#                         },
#                         {
#                             "display": user2.get_full_name(),
#                             "$ref": f"https://testserver/scim/v2/Users/{user2.uuid}",
#                             "value": str(user2.id),
#                         },
#                     ],
#                 }
#             ],
#         }

#         self.client.force_login(user=user1)
#         response = self.client.patch(
#             f"/scim/v2/Groups/{profile.uuid}", data=new_auth_data
#         )

#         self.assertEqual(status.HTTP_200_OK, response.status_code)

#         self.assertEqual(1, user1.auth_profiles.count())
#         self.assertEqual(profile, user1.auth_profiles.get())
#         self.assertEqual(1, user2.auth_profiles.count())
#         self.assertEqual(profile, user2.auth_profiles.get())

#     def test_delete_member(self):
#         user1 = SuperUserFactory.create()
#         user2 = SuperUserFactory.create()
#         profile = AuthorizationProfileFactory.create(name="Test Auth Profile")
#         user2.auth_profiles.add(profile)
#         user2.save()

#         new_auth_data = {
#             "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
#             "Operations": [
#                 {
#                     "op": "remove",
#                     "path": "members",
#                     "value": [
#                         {
#                             "display": user2.get_full_name(),
#                             "$ref": f"https://testserver/scim/v2/Users/{user2.uuid}",
#                             "value": str(user2.uuid),
#                         }
#                     ],
#                 }
#             ],
#         }

#         self.client.force_login(user=user1)
#         response = self.client.patch(
#             f"/scim/v2/Groups/{profile.uuid}", data=new_auth_data
#         )

#         self.assertEqual(status.HTTP_200_OK, response.status_code)

#         user2.refresh_from_db()

#         self.assertEqual(0, user2.auth_profiles.count())

#     def test_search_auth_profile(self):
#         profile1 = AuthorizationProfileFactory.create(name="test1")
#         profile2 = AuthorizationProfileFactory.create(name="test2")

#         search_query = {
#             "schemas": ["urn:ietf:params:scim:api:messages:2.0:SearchRequest"],
#             "filter": 'displayName eq "test1"',
#         }

#         user = SuperUserFactory.create()
#         self.client.force_login(user=user)
#         response = self.client.post("/scim/v2/Groups/.search", data=search_query)

#         self.assertEqual(status.HTTP_200_OK, response.status_code)

#         response_data = response.json()

#         self.assertEqual(1, response_data["totalResults"])
#         self.assertEqual(response_data["Resources"][0]["id"], str(profile1.uuid))

#         search_query = {
#             "schemas": ["urn:ietf:params:scim:api:messages:2.0:SearchRequest"],
#             "filter": 'displayName co "test"',
#         }

#         response = self.client.post("/scim/v2/Groups/.search", data=search_query)

#         self.assertEqual(status.HTTP_200_OK, response.status_code)

#         response_data = response.json()

#         self.assertEqual(2, response_data["totalResults"])

#     def test_cant_create_auth_profile(self):
#         user = SuperUserFactory.create()

#         self.client.force_login(user=user)
#         response = self.client.post("/scim/v2/Groups")

#         self.assertEqual(status.HTTP_405_METHOD_NOT_ALLOWED, response.status_code)

#     def test_cant_delete_auth_profile(self):
#         user = SuperUserFactory.create()
#         profile = AuthorizationProfileFactory.create()

#         self.client.force_login(user=user)
#         response = self.client.delete(f"/scim/v2/Groups/{profile.uuid}")

#         self.assertEqual(status.HTTP_405_METHOD_NOT_ALLOWED, response.status_code)


# class UserSCIMTests(APITestCase):
#     def test_user_authenticated(self):

#         response = self.client.get("/scim/v2/Users")

#         self.assertEqual(status.HTTP_401_UNAUTHORIZED, response.status_code)

#     @freeze_time("2021-08-04T09:26:22.746996+00:00")
#     def test_get_a_user(self):
#         user = SuperUserFactory.create(first_name="John", last_name="Doe")
#         auth_profile = AuthorizationProfileFactory.create()
#         user.auth_profiles.add(auth_profile)
#         user.save()

#         self.client.force_login(user=user)
#         response = self.client.get(f"/scim/v2/Users/{user.uuid}")

#         self.assertEqual(status.HTTP_200_OK, response.status_code)

#         actual_data = response.json()

#         expected_data = {
#             "id": f"{user.uuid}",
#             "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
#             "userName": f"{user.username}",
#             "name": {"givenName": "John", "familyName": "Doe", "formatted": "John Doe"},
#             "displayName": "John Doe",
#             "emails": [{"value": f"{user.username}@zac", "primary": True}],
#             "active": True,
#             "groups": [
#                 {
#                     "value": f"{auth_profile.uuid}",
#                     "$ref": f"http://testserver/scim/v2/Groups/{auth_profile.uuid}",
#                     "display": f"{auth_profile.name}",
#                 }
#             ],
#             "meta": {
#                 "resourceType": "User",
#                 "created": "2021-08-04T09:26:22.746996+00:00",
#                 "lastModified": "2021-08-04T09:26:22.746996+00:00",
#                 "location": f"http://testserver/scim/v2/Users/{user.uuid}",
#             },
#         }

#         for key, value in expected_data.items():
#             with self.subTest(key):
#                 self.assertEqual(value, actual_data[key])

#     def test_get_user_with_filter(self):
#         user1 = SuperUserFactory.create(username="hazelnut")
#         user2 = SuperUserFactory.create(username="pistachio")

#         self.client.force_login(user=user1)
#         response = self.client.get('/scim/v2/Users?filter=userName eq "pistachio"')

#         self.assertEqual(status.HTTP_200_OK, response.status_code)

#         response_data = response.json()

#         self.assertEqual(1, response_data["totalResults"])
#         self.assertEqual(str(user2.uuid), response_data["Resources"][0]["id"])

#     @freeze_time("2021-08-04T09:26:22.746996+00:00")
#     def test_create_user(self):
#         user = SuperUserFactory.create()

#         new_user_data = {
#             "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
#             "userName": "ttoast",
#             "name": {
#                 "givenName": "Test",
#                 "familyName": "Toast",
#                 "formatted": "Test Toast",
#             },
#             "displayName": "Test Toast",
#             "emails": [{"value": "ttoast@zac.nl", "primary": True}],
#             "password": "t3stPassword!",
#             "active": True,
#             "groups": [],
#         }

#         self.client.force_login(user=user)
#         response = self.client.post("/scim/v2/Users", data=new_user_data)

#         self.assertEqual(status.HTTP_201_CREATED, response.status_code)

#         actual_data = response.json()

#         new_user = User.objects.get(username="ttoast")
#         expected_data = {
#             "id": str(new_user.uuid),
#             "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
#             "userName": "ttoast",
#             "name": {
#                 "givenName": "Test",
#                 "familyName": "Toast",
#                 "formatted": "Test Toast",
#             },
#             "displayName": "Test Toast",
#             "emails": [{"value": f"ttoast@zac.nl", "primary": True}],
#             "active": True,
#             "groups": [],
#             "meta": {
#                 "resourceType": "User",
#                 "created": "2021-08-04T09:26:22.746996+00:00",
#                 "lastModified": "2021-08-04T09:26:22.746996+00:00",
#                 "location": f"http://testserver/scim/v2/Users/{new_user.uuid}",
#             },
#         }

#         self.assertEqual(2, User.objects.all().count())

#         for key, value in expected_data.items():
#             with self.subTest(key):
#                 self.assertEqual(value, actual_data[key])

#     def test_update_user(self):
#         # Note: the update (PUT) is not meant to update the groups
#         user = SuperUserFactory.create(first_name="John", last_name="Doe")

#         new_user_data = {
#             "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
#             "userName": f"{user.username}",
#             "name": {
#                 "givenName": "John",
#                 "familyName": "DoeDoe",
#                 "formatted": "John DoeDoe",
#             },
#             "displayName": "John DoeDoe",
#             "emails": [{"value": "j-doedoe@zac.nl", "primary": True}],
#         }

#         self.client.force_login(user=user)
#         response = self.client.put(f"/scim/v2/Users/{user.uuid}", data=new_user_data)

#         self.assertEqual(status.HTTP_200_OK, response.status_code)

#         self.assertEqual(1, User.objects.all().count())
#         user.refresh_from_db()

#         self.assertEqual("DoeDoe", user.last_name)
#         self.assertEqual("j-doedoe@zac.nl", user.email)

#     def test_partial_update_user(self):
#         user = SuperUserFactory.create(first_name="John", last_name="Doe")

#         new_user_data = {
#             "schemas": ["urn:ietf:params:scim:schemas:core:2.0:User"],
#             "Operations": [
#                 {"op": "replace", "path": "name.familyName", "value": "DoeDoe"}
#             ],
#         }

#         self.client.force_login(user=user)
#         response = self.client.patch(f"/scim/v2/Users/{user.uuid}", data=new_user_data)

#         self.assertEqual(status.HTTP_200_OK, response.status_code)

#         data = response.json()

#         self.assertEqual("DoeDoe", data["name"]["familyName"])
#         self.assertEqual("John DoeDoe", data["name"]["formatted"])
#         self.assertEqual("John DoeDoe", data["displayName"])

#         self.assertEqual(1, User.objects.all().count())
#         user.refresh_from_db()

#         self.assertEqual("DoeDoe", user.last_name)

#     def test_remove_user(self):
#         user1 = SuperUserFactory.create(first_name="John", last_name="Doe")
#         user2 = SuperUserFactory.create(first_name="Jane", last_name="Doe")

#         self.client.force_login(user=user2)
#         response = self.client.delete(f"/scim/v2/Users/{user1.uuid}")

#         self.assertEqual(status.HTTP_204_NO_CONTENT, response.status_code)
#         self.assertEqual(1, User.objects.filter(is_active=True).count())

#         # Check that the user is

#     def test_search_user(self):
#         user1 = SuperUserFactory.create(username="test1")
#         SuperUserFactory.create(username="test2")

#         search_query = {
#             "schemas": ["urn:ietf:params:scim:api:messages:2.0:SearchRequest"],
#             "filter": 'userName eq "test1"',
#         }

#         self.client.force_login(user=user1)
#         response = self.client.post("/scim/v2/Users/.search", data=search_query)

#         self.assertEqual(status.HTTP_200_OK, response.status_code)

#         response_data = response.json()

#         self.assertEqual(1, response_data["totalResults"])
#         self.assertEqual(response_data["Resources"][0]["id"], str(user1.uuid))

#         search_query = {
#             "schemas": ["urn:ietf:params:scim:api:messages:2.0:SearchRequest"],
#             "filter": 'userName co "test"',
#         }

#         response = self.client.post("/scim/v2/Users/.search", data=search_query)

#         self.assertEqual(status.HTTP_200_OK, response.status_code)

#         response_data = response.json()

#         self.assertEqual(2, response_data["totalResults"])
