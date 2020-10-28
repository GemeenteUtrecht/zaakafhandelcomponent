from django.urls import reverse

import requests_mock
from rest_framework.test import APITestCase

from zac.accounts.tests.factories import UserFactory

from ...models import User


class UserViewsetTests(APITestCase):
    """
    Test UserViewSet and its get_queryset function
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.users = UserFactory.create_batch(3)

        cls.superuser = User.objects.create_superuser(
            username="john", email="john.doe@johndoe.nl", password="secret"
        )

    def setUp(self):
        self.client.force_authenticate(user=self.superuser)
        self.url = reverse("accounts:users-list")

    def test_view_url_exists(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_view_search_users(self):
        params = {"search": "u"}
        response = self.client.get(self.url, params)
        self.assertEqual(response.data["count"], 3)

    def test_view_search_users_filter(self):
        usernames = [self.users[i].username for i in range(2)]

        params = {"search": "u", "exclude": usernames}
        response = self.client.get(self.url, params)
        self.assertEqual(response.data["count"], 1)

    def test_multiple_users(self):
        usernames = [self.users[i].username for i in range(2)]
        params = {"include": usernames}
        response = self.client.get(self.url, params)
        self.assertEqual(response.data["count"], 2)
