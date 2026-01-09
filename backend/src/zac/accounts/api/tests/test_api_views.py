from django.test import TestCase
from django.urls import reverse

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from zac.accounts.tests.factories import UserFactory
from zac.tests.compat import mock_service_oas_get


@requests_mock.Mocker()
class InformatieobjecttypeViewTest(APITestCase):
    def test_login_required(self, m):
        response = self.client.get("/api/accounts/informatieobjecttypen")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_no_catalogus_parameter_gives_error(self, m):
        user = UserFactory.create()
        self.client.force_authenticate(user)
        response = self.client.get(
            "/api/accounts/informatieobjecttypen",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_valid_request(self, m):
        catalog_root = "http://test.nl/api/v1/"
        catalog_url = (
            "http://test.nl/api/v1/catalogussen/1b817d02-09dc-4e5f-9c98-cc9a991b81c6"
        )
        Service.objects.create(api_type=APITypes.ztc, api_root=catalog_root)
        mock_service_oas_get(m, catalog_root, "ztc")

        m.get(
            f"{catalog_root}informatieobjecttypen?catalogus={catalog_url}",
            json={
                "count": 2,
                "next": "",
                "previous": "",
                "results": [
                    {
                        "url": f"{catalog_root}informatieobjecttypen/1",
                        "catalogus": catalog_url,
                        "vertrouwelijkheidaanduiding": "openbaar",
                        "omschrijving": "Test 1",
                        "beginGeldigheid": "2020-12-01",
                        "eindeGeldigheid": None,
                        "concept": False,
                    },
                    {
                        "url": f"{catalog_root}informatieobjecttypen/2",
                        "catalogus": catalog_url,
                        "vertrouwelijkheidaanduiding": "openbaar",
                        "omschrijving": "Test 2",
                        "beginGeldigheid": "2020-12-01",
                        "eindeGeldigheid": None,
                        "concept": False,
                    },
                ],
            },
        )

        user = UserFactory.create()
        self.client.force_authenticate(user)

        response = self.client.get(
            "/api/accounts/informatieobjecttypen", {"catalogus": catalog_url}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertIn("formData", data)
        self.assertIn("emptyFormData", data)

        self.assertEqual(len(data["emptyFormData"]), 2)
        self.assertIn("catalogus", data["emptyFormData"][0])
        self.assertIn("omschrijving", data["emptyFormData"][0])
        self.assertIn("selected", data["emptyFormData"][0])


class LogoutViewTests(TestCase):
    def test_login_required(self):
        endpoint = reverse("logout")
        response = self.client.post(endpoint)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_logout_succesful(self):
        user = UserFactory.create(password="some-secret")
        self.client.force_login(user)
        endpoint = reverse("logout")
        response = self.client.post(endpoint, user=user)
        self.assertEqual(response.status_code, 204)

        response = self.client.post(endpoint, user=user)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
