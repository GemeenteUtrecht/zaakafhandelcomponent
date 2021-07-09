from unittest import expectedFailure

from django.urls import reverse

from rest_framework.test import APITestCase

from zac.accounts.tests.factories import UserFactory

from ...models import User


class UserViewsetTests(APITestCase):
    """
    Test UserViewSet and its get_queryset function
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.users = UserFactory.create_batch(3)

        cls.superuser = User.objects.create_superuser(
            username="john", email="john.doe@johndoe.nl", password="secret"
        )

    def setUp(self):
        self.client.force_authenticate(user=self.superuser)
        self.url = reverse("users-list")

    def test_view_url_exists(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_view_search_users(self):
        params = {"search": "u"}
        response = self.client.get(self.url, params)
        self.assertEqual(response.data["count"], 3)

    def test_view_search_users_filter_username(self):
        usernames = [self.users[i].username for i in range(2)]

        params = {"search": "u", "exclude_username": usernames}
        response = self.client.get(self.url, params)
        self.assertEqual(response.data["count"], 1)

    def test_multiple_users_filter_username(self):
        usernames = [self.users[i].username for i in range(2)]
        params = {"include_username": usernames}
        response = self.client.get(self.url, params)
        self.assertEqual(response.data["count"], 2)

    def test_view_search_users_filter_email(self):
        emails = [self.users[i].email for i in range(2)]

        params = {"search": "u", "exclude_email": emails}
        response = self.client.get(self.url, params)
        self.assertEqual(response.data["count"], 1)

    def test_multiple_users_filter_email(self):
        emails = [self.users[i].email for i in range(2)]
        params = {"include_email": emails}
        response = self.client.get(self.url, params)
        self.assertEqual(response.data["count"], 2)

    @expectedFailure
    def test_multiple_users_csv(self):
        """
        Test that ?include=foo,bar works too for filtering usernames.

        Bug in django-filter, see
        https://github.com/carltongibson/django-filter/issues/1090#issuecomment-506228492

        We shouldn't rely on this anyway on the off-chance that the username contains a
        comma, which would introduce a faulty split. The preffered way is using either one
        of:

            - ``?include=foo&include=bar``
            - ``?include[]=foo&include[]=bar`` (PHP style)
        """
        usernames = [self.users[i].username for i in range(2)]
        params = {"include_username": ",".join(usernames)}
        response = self.client.get(self.url, params)
        self.assertEqual(response.data["count"], 2)
