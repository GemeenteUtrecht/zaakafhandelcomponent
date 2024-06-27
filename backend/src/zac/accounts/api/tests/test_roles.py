from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse, reverse_lazy

from rest_framework import status
from rest_framework.test import APITestCase

from zac.core.permissions import zaakproces_usertasks, zaken_inzien

from ...models import Role
from ...tests.factories import (
    RoleFactory,
    StaffUserFactory,
    SuperUserFactory,
    UserFactory,
)


class RolePermissionsTests(APITestCase):
    url = reverse_lazy("role-list")

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


class RoleAPITests(APITestCase):
    def setUp(self) -> None:
        super().setUp()

        self.user = SuperUserFactory.create()
        self.client.force_authenticate(self.user)

    def test_list_roles(self):
        role1 = RoleFactory.create(permissions=[zaken_inzien.name])
        role2 = RoleFactory.create(permissions=[zaakproces_usertasks.name])
        url = reverse("role-list")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            [
                {
                    "id": role1.id,
                    "name": role1.name,
                    "permissions": [zaken_inzien.name],
                },
                {
                    "id": role2.id,
                    "name": role2.name,
                    "permissions": [zaakproces_usertasks.name],
                },
            ],
        )

    def test_retrieve_auth_profile(self):
        role = RoleFactory.create(permissions=[zaken_inzien.name])
        url = reverse("role-detail", args=[role.id])

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {"id": role.id, "name": role.name, "permissions": [zaken_inzien.name]},
        )

    def test_create_auth_profile(self):
        url = reverse("role-list")
        data = {"name": "some name", "permissions": [zaken_inzien.name]}

        response = self.client.post(url, data=data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Role.objects.count(), 1)

        role = Role.objects.get()

        self.assertEqual(role.name, "some name")
        self.assertEqual(role.permissions, ["zaken:inzien"])

    def test_create_role_incorrect_permission_name(self):
        url = reverse("role-list")
        data = {"name": "some name", "permissions": ["some permission"]}

        response = self.client.post(url, data=data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "code": "invalid_choice",
                    "name": "permissions.0",
                    "reason": '"some permission" is een ongeldige keuze.',
                }
            ],
        )

    def test_update_role(self):
        role = RoleFactory.create(name="old name", permissions=[zaken_inzien.name])
        url = reverse("role-detail", args=[role.id])
        data = {"name": "new name", "permissions": [zaakproces_usertasks.name]}

        response = self.client.put(url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        role.refresh_from_db()

        self.assertEqual(role.name, "new name")
        self.assertEqual(role.permissions, [zaakproces_usertasks.name])

    def test_update_role_incorrect_permission_name(self):
        role = RoleFactory.create(name="old name", permissions=[zaken_inzien.name])
        url = reverse("role-detail", args=[role.id])
        data = {"name": "new name", "permissions": ["some permission"]}

        response = self.client.put(url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "code": "invalid_choice",
                    "name": "permissions.0",
                    "reason": '"some permission" is een ongeldige keuze.',
                }
            ],
        )

    def test_destroy_role(self):
        role = RoleFactory.create(name="some-name", permissions=[zaken_inzien.name])
        url = reverse("role-detail", args=[role.id])

        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        with self.assertRaises(ObjectDoesNotExist):
            role.refresh_from_db()
