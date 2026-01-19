from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen

from zac.accounts.tests.factories import UserFactory


class VertrouwelijkheidsAanduidingenTests(APITestCase):
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
        choices = [choice for choice in VertrouwelijkheidsAanduidingen.choices]
        self.assertEqual(
            response.json(),
            [{"label": choice[1], "value": choice[0]} for choice in choices],
        )
