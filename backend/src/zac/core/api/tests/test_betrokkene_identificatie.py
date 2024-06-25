from django.urls import reverse_lazy

from rest_framework.test import APITestCase

from zac.accounts.models import User
from zac.accounts.tests.factories import ApplicationTokenFactory, UserFactory
from zac.core.tests.utils import ClearCachesMixin


class RolBetrokkeneIdentificatieResponseTests(ClearCachesMixin, APITestCase):
    """
    Test the API response body for betrokkene-identificatie-retrieve-url endpoint.

    """

    endpoint = reverse_lazy(
        "betrokkene-identificatie-retrieve",
    )

    def setUp(self):
        super().setUp()

        self.token = ApplicationTokenFactory.create()
        self.headers = {"HTTP_AUTHORIZATION": f"ApplicationToken {self.token.token}"}
        self.payload = {"betrokkeneIdentificatie": {"identificatie": "user:some-user"}}

    def test_user_does_not_exist(self):
        self.assertFalse(User.objects.filter(username="some-user").exists())
        response = self.client.post(self.endpoint, self.payload, **self.headers)
        self.assertTrue(User.objects.filter(username="some-user").exists())
        self.assertEqual(
            response.json(),
            {
                "betrokkeneIdentificatie": {
                    "voorletters": "",
                    "achternaam": "",
                    "identificatie": "user:some-user",
                    "voorvoegselAchternaam": "",
                }
            },
        )

    def test_user_exists(self):
        UserFactory.create(first_name="Some", last_name="User", username="some-user")
        response = self.client.post(self.endpoint, self.payload, **self.headers)
        self.assertEqual(
            response.json(),
            {
                "betrokkeneIdentificatie": {
                    "voorletters": "S.",
                    "achternaam": "User",
                    "identificatie": "user:some-user",
                    "voorvoegselAchternaam": "",
                }
            },
        )


class RolBetrokkeneIdentificatiePermissionsTests(ClearCachesMixin, APITestCase):
    """
    Test the API permissions for betrokkene-identificatie-retrieve-url endpoint.

    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.endpoint = reverse_lazy(
            "betrokkene-identificatie-retrieve",
        )

        cls.token = ApplicationTokenFactory.create()
        cls.headers = {"HTTP_AUTHORIZATION": f"ApplicationToken {cls.token.token}"}
        cls.payload = {"betrokkeneIdentificatie": {"identificatie": "user:some-user"}}

    def test_no_token_in_header(self):
        response = self.client.post(self.endpoint, self.payload)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json()["detail"], "Authenticatiegegevens zijn niet opgegeven."
        )

    def test_wrong_http_authorization_format_in_header(self):
        response = self.client.post(
            self.endpoint, self.payload, HTTP_AUTHORIZATION="Token something"
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json()["detail"], "Authenticatiegegevens zijn niet opgegeven."
        )

    def test_correct_token_but_with_error_in_header(self):
        response = self.client.post(
            self.endpoint, self.payload, HTTP_AUTHORIZATION="ApplicationToken 12341212"
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Ongeldige token.")

    def test_correct_token(self):
        response = self.client.post(self.endpoint, self.payload, **self.headers)
        self.assertEqual(response.status_code, 200)
