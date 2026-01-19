from unittest.mock import patch

from django.urls import reverse_lazy

from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from zac.accounts.tests.factories import UserFactory


class AxesResetAPITests(APITestCase):
    endpoint = reverse_lazy("axes-reset")

    def test_permissions_not_logged_in(self):
        response = self.client.post(self.endpoint)
        self.assertEqual(response.status_code, 401)

    def test_permissions_not_staff_user(self):
        user = UserFactory.create(is_staff=False)
        token, created = Token.objects.get_or_create(user=user)
        response = self.client.post(self.endpoint, HTTP_AUTHORIZATION=f"Token {token}")
        self.assertEqual(response.status_code, 403)

    @patch("zac.accounts.management.views.reset", return_value=None)
    def test_success(self, mock_reset):
        user = UserFactory.create(is_staff=True)
        token, created = Token.objects.get_or_create(user=user)
        response = self.client.post(self.endpoint, HTTP_AUTHORIZATION=f"Token {token}")
        self.assertEqual(response.status_code, 200)
        mock_reset.assert_called_once()
        self.assertEqual(response.json(), {"count": None})

    @patch("zac.accounts.management.views.reset", return_value=10)
    def test_success_with_count(self, mock_reset):
        user = UserFactory.create(is_staff=True)
        token, created = Token.objects.get_or_create(user=user)
        response = self.client.post(self.endpoint, HTTP_AUTHORIZATION=f"Token {token}")
        self.assertEqual(response.status_code, 200)
        mock_reset.assert_called_once()
        self.assertEqual(response.json(), {"count": 10})


class ClearRecentlyViewedAPITests(APITestCase):
    endpoint = reverse_lazy("recently-viewed-clear")

    def test_permissions_not_logged_in(self):
        response = self.client.post(self.endpoint)
        self.assertEqual(response.status_code, 401)

    def test_permissions_not_staff_user(self):
        user = UserFactory.create(is_staff=False)
        token, created = Token.objects.get_or_create(user=user)
        response = self.client.post(self.endpoint, HTTP_AUTHORIZATION=f"Token {token}")
        self.assertEqual(response.status_code, 403)

    def test_success(self):
        user = UserFactory.create(is_staff=True)
        token, created = Token.objects.get_or_create(user=user)
        user.recently_viewed = [{"some-data"}]

        response = self.client.post(self.endpoint, HTTP_AUTHORIZATION=f"Token {token}")
        self.assertEqual(response.status_code, 204)
        user.refresh_from_db()
        self.assertFalse(user.recently_viewed)
