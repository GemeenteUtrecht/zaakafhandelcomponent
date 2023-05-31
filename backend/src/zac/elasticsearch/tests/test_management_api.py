from unittest.mock import patch

from django.urls import reverse_lazy

from rest_framework.test import APITestCase

from zac.accounts.tests.factories import UserFactory


class IndexAllAPITests(APITestCase):
    endpoint = reverse_lazy("index-all")

    def test_permissions_not_logged_in(self):
        response = self.client.post(self.endpoint)
        self.assertEqual(response.status_code, 403)

    def test_permissions_not_staff_user(self):
        user = UserFactory.create(is_staff=False)
        self.client.force_authenticate(user)
        response = self.client.post(self.endpoint)
        self.assertEqual(response.status_code, 403)

    @patch("zac.elasticsearch.management.views.call_command")
    def test_success(self, mock_call_command):
        user = UserFactory.create(is_staff=True)
        self.client.force_authenticate(user)
        response = self.client.post(self.endpoint)
        self.assertEqual(response.status_code, 204)
        mock_call_command.assert_called_once_with("index_all")
