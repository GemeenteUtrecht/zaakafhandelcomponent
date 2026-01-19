from django.test import override_settings
from django.urls import reverse_lazy

import requests_mock
from furl import furl
from rest_framework import status
from rest_framework.test import APITestCase


@override_settings(
    EXTERNAL_API_SCHEMAS={"SOME_API_SCHEMA": "https://some-schema-url.com/"}
)
class RemoteSchemaViewTests(APITestCase):
    schema_endpoint = reverse_lazy("get-remote-schema")

    @requests_mock.Mocker()
    def test_200_ok(self, m):
        endpoint = furl(self.schema_endpoint).set(
            {"schema": "https://some-schema-url.com/"}
        )
        m.get("https://some-schema-url.com/")
        response = self.client.get(endpoint.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_403_not_allowed(self):
        endpoint = furl(self.schema_endpoint).set(
            {"schema": "https://some-not-allowed-url.com/"}
        )
        response = self.client.get(endpoint.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
