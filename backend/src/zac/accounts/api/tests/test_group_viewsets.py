from django.urls import reverse

from rest_framework.test import APITestCase

from zac.accounts.tests.factories import GroupFactory, SuperUserFactory


class GroupViewsetTests(APITestCase):
    """
    Test GroupViewSet and search

    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.groups = GroupFactory.create_batch(3)
        cls.superuser = SuperUserFactory.create()

    def setUp(self):
        self.client.force_authenticate(user=self.superuser)
        self.url = reverse("groups-list")

    def test_view_search_groups(self):
        params = {"search": "u"}
        response = self.client.get(self.url, params)
        self.assertEqual(response.data["count"], 3)
