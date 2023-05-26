from django.contrib.auth.models import Group
from django.urls import reverse

from rest_framework.test import APITestCase

from zac.accounts.tests.factories import GroupFactory, SuperUserFactory, UserFactory


class GroupViewsetTests(APITestCase):
    """
    Test GroupViewSet and search

    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.groups = GroupFactory.create_batch(3)
        cls.user = UserFactory.create()

    def test_search_no_authentication_no_results(self):
        params = {"search": "u"}
        response = self.client.get(reverse("usergroups-list"), params)
        self.assertEqual(response.status_code, 403)

    def test_view_search_groups(self):
        self.client.force_authenticate(user=self.user)
        params = {"search": "u"}
        response = self.client.get(reverse("usergroups-list"), params)
        self.assertEqual(response.data["count"], 3)
        self.assertFalse("users" in response.data["results"][0])

    def test_search_no_permission_needed_to_search_or_list(self):
        self.client.force_authenticate(user=self.user)
        params = {"search": "u"}
        response = self.client.get(reverse("usergroups-list"), params)
        self.assertEqual(response.data["count"], 3)

    def test_detail_no_permission(self):
        self.client.force_authenticate(user=self.user)
        detail_endpoint = reverse("usergroups-detail", args=[self.groups[0].id])
        response = self.client.get(detail_endpoint)
        self.assertEqual(response.status_code, 403)

    def test_detail_with_permission(self):
        self.client.force_authenticate(user=self.user)
        self.user.groups.add(*self.groups)
        detail_endpoint = reverse("usergroups-detail", args=[self.groups[0].id])
        response = self.client.get(detail_endpoint)
        self.assertEqual(response.status_code, 200)

    def test_group_creation_permissions(self):
        self.client.force_authenticate(user=self.user)
        endpoint = reverse("usergroups-list")
        data = {"name": "Some-group-name", "users": [self.user.username]}
        response = self.client.post(endpoint, data)
        self.assertEqual(response.status_code, 201)

        self.assertTrue(Group.objects.filter(name="Some-group-name").exists())
        group = Group.objects.get(name="Some-group-name")
        self.assertTrue(group in self.user.manages_groups.all())

        self.user.manages_groups.remove(group)
        self.user.groups.remove(group)

    def test_group_no_update_permissions(self):
        self.client.force_authenticate(user=self.user)
        detail_endpoint = reverse("usergroups-detail", args=[self.groups[0].id])
        data = {"users": [self.user.username]}
        response = self.client.post(detail_endpoint, data)
        self.assertEqual(response.status_code, 403)

    def test_group_with_update_permissions(self):
        self.client.force_authenticate(user=self.user)
        self.user.manages_groups.add(self.groups[0])
        detail_endpoint = reverse("usergroups-detail", args=[self.groups[0].id])
        data = {"name": self.groups[0].name, "users": [self.user.username]}
        response = self.client.put(detail_endpoint, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "id": self.groups[0].id,
                "name": self.groups[0].name,
                "fullName": "Groep: " + self.groups[0].name,
                "users": [
                    {
                        "id": self.user.id,
                        "username": self.user.username,
                        "firstName": self.user.first_name,
                        "fullName": self.user.get_full_name(),
                        "lastName": self.user.last_name,
                        "isStaff": self.user.is_staff,
                        "email": self.user.email,
                        "groups": [self.groups[0].name],
                    }
                ],
            },
        )
        self.user.manages_groups.remove(self.groups[0])
        self.user.groups.remove(self.groups[0])

    def test_group_with_superuser(self):
        superuser = SuperUserFactory.create()
        self.client.force_authenticate(user=superuser)
        detail_endpoint = reverse("usergroups-detail", args=[self.groups[0].id])
        data = {"name": self.groups[0].name, "users": [self.user.username]}
        response = self.client.put(detail_endpoint, data)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "id": self.groups[0].id,
                "name": self.groups[0].name,
                "fullName": "Groep: " + self.groups[0].name,
                "users": [
                    {
                        "id": self.user.id,
                        "username": self.user.username,
                        "firstName": self.user.first_name,
                        "fullName": self.user.get_full_name(),
                        "lastName": self.user.last_name,
                        "isStaff": self.user.is_staff,
                        "email": self.user.email,
                        "groups": [self.groups[0].name],
                    }
                ],
            },
        )
