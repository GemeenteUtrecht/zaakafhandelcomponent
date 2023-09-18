from unittest.mock import patch

from django.urls import reverse_lazy

from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from zac.accounts.tests.factories import UserFactory


class IndexAllAPITests(APITestCase):
    endpoint = reverse_lazy("index-all")

    def test_permissions_not_token_authenticated(self):
        response = self.client.post(self.endpoint)
        self.assertEqual(response.status_code, 401)

    def test_permissions_not_staff_user(self):
        user = UserFactory.create(is_staff=False)
        token, created = Token.objects.get_or_create(user=user)
        response = self.client.post(self.endpoint, HTTP_AUTHORIZATION=f"Token {token}")
        self.assertEqual(response.status_code, 403)

    @patch("zac.elasticsearch.management.views.call_command")
    def test_success(self, mock_call_command):
        user = UserFactory.create(is_staff=True)
        token, created = Token.objects.get_or_create(user=user)
        response = self.client.post(self.endpoint, HTTP_AUTHORIZATION=f"Token {token}")
        self.assertEqual(response.status_code, 204)
        mock_call_command.assert_called_once_with("index_all")
