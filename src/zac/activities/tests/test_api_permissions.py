from django.urls import reverse_lazy

from rest_framework import status
from rest_framework.test import APITestCase

from zac.accounts.tests.factories import UserFactory

from .factories import ActivityFactory


class ReadPermissionTests(APITestCase):

    endpoint = reverse_lazy("activities:activity-list")

    def test_read_not_logged_in(self):
        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_read_logged_in_no_filter(self):
        user = UserFactory.create()
        self.client.force_login(user)
        ActivityFactory.create()

        response = self.client.get(self.endpoint)

        self.assertEqual(response.data, [])
