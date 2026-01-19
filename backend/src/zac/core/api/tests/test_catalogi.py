from django.urls import reverse

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.constants import APITypes

from zac.accounts.tests.factories import SuperUserFactory, UserFactory
from zac.core.tests.utils import ClearCachesMixin
from zac.tests import ServiceFactory
from zac.tests.compat import generate_oas_component, mock_service_oas_get
from zac.tests.utils import paginated_response

CATALOGI_ROOT = "http://catalogus.nl/api/v1/"
CATALOGUS_URL = f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"


@requests_mock.Mocker()
class CatalogiPermissiontests(ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        ServiceFactory.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)

        cls.catalogus = generate_oas_component(
            "ztc", "schemas/Catalogus", url=CATALOGUS_URL, domein="some-domein"
        )

        cls.endpoint = reverse("catalogi")

    def test_not_authenticated(self, m):
        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}catalogussen",
            json=paginated_response([self.catalogus]),
        )
        user = UserFactory.create()
        self.client.force_authenticate(user=user)
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)


@requests_mock.Mocker()
class CatalogiResponseTests(ClearCachesMixin, APITestCase):
    """
    Test the API response body for catalogi endpoint.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = SuperUserFactory.create()

        ServiceFactory.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)

        cls.endpoint = reverse("catalogi")

    def setUp(self):
        super().setUp()

        # ensure that we have a user with all permissions
        self.client.force_authenticate(user=self.user)

    def test_list_catalogi(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

        catalogus = generate_oas_component(
            "ztc", "schemas/Catalogus", url=CATALOGUS_URL, domein="some-domein"
        )
        m.get(
            f"{CATALOGI_ROOT}catalogussen",
            json=paginated_response([catalogus]),
        )

        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(), [{"domein": "some-domein", "url": CATALOGUS_URL}]
        )
