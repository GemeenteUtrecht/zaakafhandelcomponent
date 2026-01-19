from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse, reverse_lazy

from rest_framework import status

from zac.elasticsearch.tests.utils import ESMixin

from ..models import User
from .factories import StaffUserFactory


@override_settings(AXES_ENABLED=False)
class HijackHeaderTests(ESMixin, TestCase):
    def setUp(self):
        super().setUp()

        User.objects.create_superuser(
            username="superuser", password="superuser_pw", email="superuser@example.com"
        )
        self.client.login(username="superuser", password="superuser_pw")

        # some BFF endpoints to check the header
        self.urls = [
            reverse_lazy("zaaktypen"),
            reverse_lazy("users-list"),
            reverse_lazy("werkvoorraad:cases"),
        ]

    def test_response_not_hijacked(self):
        for url in self.urls:
            with self.subTest(url):

                response = self.client.get(url)

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertIn(settings.HIJACK_HEADER, response)
                self.assertEqual(response[settings.HIJACK_HEADER], "false")

    def test_response_hijacked(self):
        user_to_hijack = StaffUserFactory.create()
        # hijack the user
        hijack_url = reverse("hijack:acquire")
        self.client.post(hijack_url, {"user_pk": user_to_hijack.pk})

        for url in self.urls:
            with self.subTest(url):
                response = self.client.get(url)

                self.assertEqual(
                    response.status_code, status.HTTP_200_OK, response.json()
                )
                self.assertIn(settings.HIJACK_HEADER, response)
                self.assertEqual(response[settings.HIJACK_HEADER], "true")
