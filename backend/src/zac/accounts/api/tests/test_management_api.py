from unittest.mock import patch

from django.urls import reverse_lazy

from rest_framework.test import APITestCase

from zac.accounts.tests.factories import UserFactory


class AxesResetAPITests(APITestCase):
    endpoint = reverse_lazy("axes-reset")

    def test_permissions_not_logged_in(self):
        response = self.client.post(self.endpoint)
        self.assertEqual(response.status_code, 403)

    def test_permissions_not_staff_user(self):
        user = UserFactory.create(is_staff=False)
        self.client.force_authenticate(user)
        response = self.client.post(self.endpoint)
        self.assertEqual(response.status_code, 403)

    @patch("zac.accounts.management.views.reset", return_value=None)
    def test_success(self, mock_reset):
        user = UserFactory.create(is_staff=True)
        self.client.force_authenticate(user)
        response = self.client.post(self.endpoint)
        self.assertEqual(response.status_code, 200)
        mock_reset.assert_called_once()
        self.assertEqual(response.json(), {"count": None})

    @patch("zac.accounts.management.views.reset", return_value=10)
    def test_success_with_count(self, mock_reset):
        user = UserFactory.create(is_staff=True)
        self.client.force_authenticate(user)
        response = self.client.post(self.endpoint)
        self.assertEqual(response.status_code, 200)
        mock_reset.assert_called_once()
        self.assertEqual(response.json(), {"count": 10})
