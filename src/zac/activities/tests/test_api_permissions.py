from django.urls import reverse_lazy

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.models import APITypes, Service

from zac.accounts.tests.factories import UserFactory
from zac.tests.utils import generate_oas_component, mock_service_oas_get

from .factories import ActivityFactory

ZAKEN_ROOT = "https://open-zaak.nl/zaken/api/v1/"
CATALOGI_ROOT = "https://open-zaak.nl/catalogi/api/v1/"


class ReadPermissionTests(APITestCase):
    """
    Test the activity list endpoint permissions.

    These tests build up from top-to-bottom in increased permissions, starting with
    a user who's not logged in at all. Every test adds a little extra that satisfies
    the previous test, until eventually permissions are effectively set and a succesful,
    auth controlled read is performed.
    """

    endpoint = reverse_lazy("activities:activity-list")

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        Service.objects.create(
            label="Zaken API", api_type=APITypes.zrc, api_root=ZAKEN_ROOT
        )

    def test_read_not_logged_in(self):
        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_read_logged_in_no_filter(self):
        user = UserFactory.create()
        self.client.force_login(user)
        ActivityFactory.create()

        response = self.client.get(self.endpoint)

        self.assertEqual(response.data, [])

    @requests_mock.Mocker()
    def test_read_logged_in_zaak_no_permission(self, m):
        user = UserFactory.create()
        self.client.force_login(user)
        ActivityFactory.create()
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7",
            zaaktype=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
        )
        m.get(zaak["url"], json=zaak)

        response = self.client.get(self.endpoint, {"zaak": zaak["url"]})

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
