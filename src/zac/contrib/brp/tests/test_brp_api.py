from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

import requests_mock

from zgw_consumers.constants import APITypes, AuthTypes
from zgw_consumers.models import Service

from zac.core.tests.utils import ClearCachesMixin
from zac.tests.utils import mock_service_oas_get
from zac.accounts.models import User

from ..api import fetch_natuurlijkpersoon, get_client, call_client, fetch_extrainfo_np
from ..models import BRPConfig

BRP_API_ROOT = "https://brp.nl/api/v1/"
PERSOON_URL = f"{BRP_API_ROOT}ingeschrevenpersonen/123456782"


class BrpApiTests(ClearCachesMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.service = Service.objects.create(
            label="BRP",
            api_type=APITypes.orc,
            api_root=BRP_API_ROOT,
            auth_type=AuthTypes.api_key,
            header_key="Authorization",
            header_value="Token foobarbaz",
            oas=f"{BRP_API_ROOT}schema",
        )
        config = BRPConfig.get_solo()
        config.service = cls.service
        config.save()

    def _setUpMock(self, m):
        # generate_oas_component doesn't support allOf objects
        naturlijk_persoon = {
            "burgerservicenummer": "123456782",
            "geslachtsaanduiding": "man",
            "leeftijd": 34,
            "kiesrecht": {},
            "naam": {},
            "geboorte": {'datum':{'datum':'31-03-1989'},'land':{'omschrijving':'Nederland'}},
            "_links": {},
        }
        mock_service_oas_get(m, self.service.api_root, "brp", oas_url=self.service.oas)
        m.get(PERSOON_URL, json=naturlijk_persoon)

    @requests_mock.Mocker()
    def test_client(self, m):
        self._setUpMock(m)

        client = get_client()

        self.assertIsInstance(client.schema, dict)
        self.assertIsNone(client.auth)
        self.assertEqual(client.auth_header, {"Authorization": "Token foobarbaz"})
        self.assertEqual(len(m.request_history), 1)
        self.assertEqual(m.last_request.url, f"{self.service.oas}?v=3")

    @requests_mock.Mocker()
    def test_fetch_naturlijk_persoon(self, m):
        self._setUpMock(m)

        result = fetch_natuurlijkpersoon(PERSOON_URL)

        self.assertEqual(result.burgerservicenummer, "123456782")

        headers = m.last_request.headers
        self.assertEqual(headers["Authorization"], "Token foobarbaz")
        self.assertEqual(headers["Content-Type"], "application/hal+json")
        self.assertEqual(headers["Accept"], "application/hal+json")

    @requests_mock.Mocker()
    def test_fetch_extrainfo_np_doelbinding(self, m):
        self._setUpMock(m)

        doelbinding = 'test'
        query_params = {'doelbinding': [doelbinding]}
        fetch_extrainfo_np('123456782', query_params)
        headers = m.last_request.headers
        self.assertEqual(headers['X-NLX-Request-Subject-Identifier'], doelbinding)

    @requests_mock.Mocker()
    def test_fetch_extrainfo_np_fields(self, m):
        self._setUpMock(m)

        doelbinding = 'test'
        query_params = {'doelbinding': [doelbinding], 'fields': ['geboorte.land', 'geboorte.datum']}
        result = fetch_extrainfo_np('123456782', query_params)
        self.assertEqual(result.geboortedatum, '31-03-1989')
        self.assertEqual(result.geboorteland, 'Nederland')


class BrpApiViewTests(APITestCase):
    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username='john',
            email='john.doe@johndoe.nl',
            password='secret')

        self.client.force_authenticate(user=self.superuser)
        self.base_url = reverse('core:get-betrokkene-info', args=['123456782'])

    def test_betrokkene_api_no_query_parameters(self):
        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 400)

    def test_betrokkene_api_no_valid_doelbinding(self):
        url_no_value_doelbinding = self.base_url + '?doelbinding='
        response = self.client.get(url_no_value_doelbinding)
        self.assertEqual(response.status_code, 400)

    def test_betrokkene_api_no_fields(self):
        url_no_fields = self.base_url + '?doelbinding=test'
        response = self.client.get(url_no_fields)
        self.assertEqual(response.status_code, 400)

    def test_betrokkene_api_no_valid_fields(self):
        url_no_fields = self.base_url + '?doelbinding=test&fields=test,hello'
        response = self.client.get(url_no_fields)
        self.assertEqual(response.status_code, 400)

