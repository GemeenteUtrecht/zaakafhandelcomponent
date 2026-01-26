from importlib import import_module

from django.conf import settings
from django.http import HttpRequest
from django.test import override_settings
from django.urls import reverse_lazy

from axes.conf import settings
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase

from zac.accounts.tests.factories import UserFactory


@override_settings(SESSION_COOKIE_AGE=60)
class PingViewTests(APITestCase):
    endpoint = reverse_lazy("ping")

    def test_200_ok(self):
        user = UserFactory.create()
        self.client.force_authenticate(user)
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {"pong": True})

    def test_403_not_authenticated(self):
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_403_expired(self):
        user = UserFactory()
        user.set_password("some-secret")
        user.save()
        engine = import_module(settings.SESSION_ENGINE)
        request = HttpRequest()
        request.session = engine.SessionStore()

        with freeze_time("2024-01-01 12:00:00"):
            response = self.client.login(
                request=request, username=user.username, password="some-secret"
            )
        with freeze_time("2024-01-01 12:01:01"):
            response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_200_extended(self):
        user = UserFactory()
        user.set_password("some-secret")
        user.save()
        engine = import_module(settings.SESSION_ENGINE)
        request = HttpRequest()
        request.session = engine.SessionStore()

        with freeze_time("2024-01-01 12:00:00"):
            response = self.client.login(
                request=request, username=user.username, password="some-secret"
            )
        with freeze_time("2024-01-01 12:00:59"):
            response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        with freeze_time("2024-01-01 12:01:58"):
            response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
