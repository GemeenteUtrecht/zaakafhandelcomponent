from unittest.mock import patch

from django.core.cache import cache
from django.urls import reverse_lazy

from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from zac.accounts.tests.factories import UserFactory
from zac.core.tests.utils import ClearCachesMixin


class CacheResetAPITests(ClearCachesMixin, APITestCase):
    endpoint = reverse_lazy("cache-reset")

    def test_permissions_not_logged_in(self):
        response = self.client.post(self.endpoint)
        self.assertEqual(response.status_code, 401)

    def test_permissions_not_staff_user(self):
        user = UserFactory.create(is_staff=False)
        token, created = Token.objects.get_or_create(user=user)
        response = self.client.post(self.endpoint, HTTP_AUTHORIZATION=f"Token {token}")
        self.assertEqual(response.status_code, 403)

    def test_success_key(self):
        user = UserFactory.create(is_staff=True)
        cache.set("some-key", "some-val")
        data = {"key": "some-key"}
        token, created = Token.objects.get_or_create(user=user)
        response = self.client.post(
            self.endpoint, data=data, HTTP_AUTHORIZATION=f"Token {token}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"count": 1, "key": "some-key"})

    def test_success_key_no_cache(self):
        user = UserFactory.create(is_staff=True)
        data = {"key": "some-key"}
        token, created = Token.objects.get_or_create(user=user)
        response = self.client.post(
            self.endpoint, data=data, HTTP_AUTHORIZATION=f"Token {token}"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"count": 0, "key": "some-key"})

    @patch("zac.core.management.serializers.is_redis_cache", return_value=False)
    def test_fail_pattern_no_redis_cache(self, mock_is_redis_cache):
        user = UserFactory.create(is_staff=True)
        data = {"pattern": "*"}
        token, created = Token.objects.get_or_create(user=user)
        response = self.client.post(
            self.endpoint, data=data, HTTP_AUTHORIZATION=f"Token {token}"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()['invalidParams'],
            [
                {
                    "name": "nonFieldErrors",
                    "code": "invalid",
                    "reason": "Pattern is not allowed for non-redis caches. Please provide a key.",
                }
            ],
        )

    @patch("zac.core.management.serializers.is_redis_cache", return_value=True)
    @patch("zac.core.management.serializers.cache")
    def test_success_pattern_mock_redis_cache(self, mock_cache, mock_is_redis_cache):
        user = UserFactory.create(is_staff=True)
        data = {"pattern": "*"}
        token, created = Token.objects.get_or_create(user=user)
        with patch(
            "zac.core.management.serializers.cache.delete_pattern", return_value=10
        ):
            response = self.client.post(
                self.endpoint, data=data, HTTP_AUTHORIZATION=f"Token {token}"
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"count": 10, "pattern": "*"})

    @patch("zac.core.management.serializers.is_redis_cache", return_value=True)
    @patch("zac.core.management.serializers.cache")
    def test_success_pattern_and_key_mock_redis_cache(
        self, mock_cache, mock_is_redis_cache
    ):
        user = UserFactory.create(is_staff=True)
        token, created = Token.objects.get_or_create(user=user)
        data = {"pattern": "*", "key": "some-key"}
        cache.set("some-key", "some-val")
        with patch(
            "zac.core.management.serializers.cache.delete_pattern", return_value=10
        ):

            response = self.client.post(
                self.endpoint, data=data, HTTP_AUTHORIZATION=f"Token {token}"
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(), {"count": 11, "pattern": "*", "key": "some-key"}
        )
