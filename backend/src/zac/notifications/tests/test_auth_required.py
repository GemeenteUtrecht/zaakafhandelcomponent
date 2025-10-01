from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase


class AuthTests(APITestCase):
    def test_auth_required_callback(self):
        url = reverse("notifications:callback")

        # no credentials → should reject
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
