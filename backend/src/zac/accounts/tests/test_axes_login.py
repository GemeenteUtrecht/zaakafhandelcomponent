from importlib import import_module
from unittest.mock import patch

from django.conf import settings
from django.http import HttpRequest
from django.test import TestCase, override_settings
from django.urls import reverse_lazy

from axes.conf import settings
from axes.models import AccessAttempt

from zac.accounts.tests.factories import UserFactory

IP = "127.1.0.1"


@override_settings(
    AXES_FAILURE_LIMIT=2,
    AXES_LOCKOUT_PARAMETERS=[["username", "ip_address"]],
    AXES_COOLOFF_TIME=None,
    AXES_RESET_ON_SUCCESS=True,
)
class LockOutTestCase(TestCase):
    url = reverse_lazy("accounts:login")

    def test_login_success_on_combination_user_and_ip(self):
        user = UserFactory()
        user.set_password("some-secret")
        user.save()

        engine = import_module(settings.SESSION_ENGINE)
        request = HttpRequest()
        request.session = engine.SessionStore()
        request.META["REMOTE_ADDR"] = IP
        response = self.client.login(
            request=request, username=user.username, password="some-secret"
        )
        self.assertTrue(response)
        self.assertEqual(AccessAttempt.objects.count(), 0)

    def test_lockout_on_combination_user_and_ip(self):
        user = UserFactory()
        user.set_password("some-secret")
        user.save()

        engine = import_module(settings.SESSION_ENGINE)
        request = HttpRequest()
        request.session = engine.SessionStore()
        request.META["REMOTE_ADDR"] = IP

        login_attempts_to_make = settings.AXES_FAILURE_LIMIT
        for i in range(login_attempts_to_make):
            self.client.login(
                request=request,
                username=user.username,
                password="some-other-password",
            )

        self.assertEqual(AccessAttempt.objects.count(), 1)

    def test_lockout_on_combination_user_and_ip_allow_other_user_to_login_from_same_ip(
        self,
    ):
        user = UserFactory()
        user.set_password("some-secret")
        user.save()

        engine = import_module(settings.SESSION_ENGINE)
        request = HttpRequest()
        request.session = engine.SessionStore()
        request.META["REMOTE_ADDR"] = IP
        for i in range(settings.AXES_FAILURE_LIMIT + 1):
            response = self.client.login(
                request=request, username=user.username, password="some-other-secret"
            )
        self.assertFalse(response)
        self.assertEqual(AccessAttempt.objects.count(), 1)

        user = UserFactory()
        user.set_password("some-secret")
        user.save()
        engine = import_module(settings.SESSION_ENGINE)
        request = HttpRequest()
        request.session = engine.SessionStore()
        request.META["REMOTE_ADDR"] = IP
        response = self.client.login(
            request=request, username=user.username, password="some-secret"
        )
        self.assertTrue(response)
        self.assertEqual(AccessAttempt.objects.count(), 1)

    @patch("axes.helpers.ipware.ip.get_client_ip", return_value=(IP, None))
    def test_reset_on_success_on_combination_user_and_ip(self, mock_get_client_ip):
        user = UserFactory()
        user.set_password("some-secret")
        user.save()

        engine = import_module(settings.SESSION_ENGINE)
        request = HttpRequest()
        request.session = engine.SessionStore()
        request.META["REMOTE_ADDR"] = IP

        for i in range(settings.AXES_FAILURE_LIMIT - 1):
            response = self.client.login(
                request=request, username=user.username, password="some-other-secret"
            )
        self.assertFalse(response)
        self.assertEqual(AccessAttempt.objects.count(), 1)

        response = self.client.login(
            request=request, username=user.username, password="some-secret"
        )
        self.assertTrue(response)
        self.assertEqual(AccessAttempt.objects.count(), 0)
