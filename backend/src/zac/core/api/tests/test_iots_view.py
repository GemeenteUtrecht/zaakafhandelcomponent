from unittest.mock import patch

from django.test import override_settings
from django.urls import reverse

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.constants import APITypes

from zac.accounts.tests.factories import SuperUserFactory, UserFactory
from zac.core.tests.utils import ClearCachesMixin, mock_parallel
from zac.tests import ServiceFactory
from zac.tests.compat import generate_oas_component, mock_service_oas_get
from zac.tests.utils import mock_resource_get, paginated_response

CATALOGI_ROOT = "http://catalogus.nl/api/v1/"
CATALOGUS_URL = f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
ZAKEN_ROOT = "http://zaken.nl/api/v1/"
ZAAK_URL = f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950"


@requests_mock.Mocker()
class InformatieObjectTypesPermissiontests(ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        ServiceFactory.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        ServiceFactory.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        cls.catalogus = generate_oas_component(
            "ztc",
            "schemas/Catalogus",
            url=CATALOGUS_URL,
        )
        cls.iot = generate_oas_component(
            "ztc",
            "schemas/InformatieObjectType",
            catalogus=CATALOGUS_URL,
            url=f"{CATALOGI_ROOT}informatieobjecttypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            catalogus=CATALOGUS_URL,
        )
        cls.ziot = generate_oas_component(
            "ztc",
            "schemas/ZaakTypeInformatieObjectType",
            zaaktype=cls.zaaktype["url"],
            informatieobjecttype=cls.iot["url"],
        )
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            zaaktype=cls.zaaktype["url"],
        )

        cls.endpoint = reverse("informatieobjecttypes-list") + f"?zaak={ZAAK_URL}"

    def test_not_authenticated(self, m):
        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch("zac.core.services.parallel", return_value=mock_parallel())
    def test_authenticated(self, m, m_parallel):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaak)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.iot)
        m.get(
            f"{CATALOGI_ROOT}zaaktype-informatieobjecttypen",
            json=paginated_response([self.ziot]),
        )
        user = UserFactory.create()
        self.client.force_authenticate(user=user)
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)


@requests_mock.Mocker()
class InformatieObjectTypesResponseTests(ClearCachesMixin, APITestCase):
    """
    Test the API response body for IOTs endpoint.

    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = SuperUserFactory.create()

        ServiceFactory.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        ServiceFactory.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)

        cls.catalogus = generate_oas_component(
            "ztc",
            "schemas/Catalogus",
            url=CATALOGUS_URL,
        )
        cls.iot = generate_oas_component(
            "ztc",
            "schemas/InformatieObjectType",
            catalogus=CATALOGUS_URL,
            url=f"{CATALOGI_ROOT}informatieobjecttypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            omschrijving="ZOMAAR EEN IOT",
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            catalogus=CATALOGUS_URL,
        )
        cls.ziot = generate_oas_component(
            "ztc",
            "schemas/ZaakTypeInformatieObjectType",
            zaaktype=cls.zaaktype["url"],
            informatieobjecttype=cls.iot["url"],
        )
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            zaaktype=cls.zaaktype["url"],
        )

        cls.endpoint = reverse("informatieobjecttypes-list") + f"?zaak={ZAAK_URL}"

    def setUp(self):
        super().setUp()

        # ensure that we have a user with all permissions
        self.client.force_authenticate(user=self.user)

    @patch("zac.core.services.parallel", return_value=mock_parallel())
    def test_list_iots(self, m, m_parallel):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaak)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.iot)
        m.get(
            f"{CATALOGI_ROOT}zaaktype-informatieobjecttypen",
            json=paginated_response([self.ziot]),
        )

        response = self.client.get(self.endpoint, query_params={"zaak": ZAAK_URL})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)

    @override_settings(FILTERED_IOTS=["ZOMAAR EEN IOT"])
    @patch("zac.core.services.parallel", return_value=mock_parallel())
    def test_list_iots_filtered(self, m, *mocks):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaak)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.iot)
        m.get(
            f"{CATALOGI_ROOT}zaaktype-informatieobjecttypen",
            json=paginated_response([self.ziot]),
        )

        response = self.client.get(self.endpoint, query_params={"zaak": ZAAK_URL})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 0)
