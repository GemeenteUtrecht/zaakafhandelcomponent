from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase


class AuthTests(APITestCase):
    def test_auth_required_callback(self):
        url = reverse("notifications:callback")

        # no credentials → should reject
        response = self.client.post(url)

        # DRF normally returns 401 for unauthenticated requests
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
