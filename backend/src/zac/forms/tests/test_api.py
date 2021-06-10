import json
from unittest.mock import patch

from django.urls import reverse

from rest_framework.test import APITestCase

from zac.accounts.tests.factories import SuperUserFactory


class ResponseTests(APITestCase):
    def setUp(self):
        user = SuperUserFactory.create()
        self.client.force_authenticate(user=user)

    @patch("zac.forms.client.OpenFormsClient.__init__")
    @patch("zac.forms.client.OpenFormsClient.get_forms")
    def test_200(self, mock_get_forms, mock_init):
        mock_get_forms.return_value = [
            {
                "id": 1,
                "name": "Een formulier",
                "slug": "een formulier",
                "layouts": ["default"],
            }
        ]
        mock_init.return_value = None

        endpoint = reverse("form-api-list")
        response = self.client.get(endpoint, follow=True)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertEqual(data, mock_get_forms.return_value)
