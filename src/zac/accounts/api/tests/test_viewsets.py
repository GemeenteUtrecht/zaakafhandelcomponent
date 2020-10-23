from django.urls import reverse

import requests_mock
from rest_framework.test import APITestCase

from ...models import User


class UserViewsetTests(APITestCase):
    """
    Test UserViewSet and its get_queryset function
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        fake_users = ["lol", "hoi", "hihi"]
        for fake_user in fake_users:
            user = User.objects.create_user(username=fake_user)
            user.save()

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
        search_url = self.url + "?search=h"
        response = self.client.get(search_url)
        self.assertEqual(response.data["count"], 3)

    def test_view_search_users_filter(self):
        search_url = self.url + "?search=h&filter_users=lol,hihi"
        response = self.client.get(search_url)
        self.assertEqual(response.data["count"], 2)

    def test_multiple_users(self):
        search_url = self.url + "?filter_users=lol,hihi&include=True"
        response = self.client.get(search_url)
        self.assertEqual(response.data["count"], 2)
