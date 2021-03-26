from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITransactionTestCase
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen

from zac.accounts.tests.factories import UserFactory


class VertrouwelijkheidsAanduidingenTests(APITransactionTestCase):
    def setUp(self):
        super().setUp()
        self.endpoint = reverse("confidentiality-classications")

    def test_not_authenticated(self):
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated(self):
        user = UserFactory.create()
        self.client.force_authenticate(user=user)
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "classifications": [
                    {"label": choice[0], "value": choice[1]}
                    for choice in VertrouwelijkheidsAanduidingen.choices
                ]
            },
        )
