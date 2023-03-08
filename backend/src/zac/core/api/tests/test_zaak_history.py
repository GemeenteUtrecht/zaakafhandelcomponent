from unittest import mock
from unittest.mock import patch

from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse

import requests_mock
from freezegun import freeze_time
from requests.exceptions import HTTPError
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ResultaatType, ZaakType
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.api_models.zaken import Resultaat
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import (
    AccessRequestFactory,
    AtomicPermissionFactory,
    BlueprintPermissionFactory,
    SuperUserFactory,
    UserFactory,
)
from zac.contrib.kownsl.models import KownslConfig
from zac.core.models import CoreConfig, MetaObjectTypesConfig
from zac.core.permissions import (
    zaken_geforceerd_bijwerken,
    zaken_inzien,
    zaken_wijzigen,
)
from zac.core.tests.utils import ClearCachesMixin
from zac.elasticsearch.tests.utils import ESMixin
from zac.tests.utils import mock_resource_get, paginated_response
from zgw.models.zrc import Zaak

ZAKEN_ROOT = "http://zaken.nl/api/v1/"
BRONORGANISATIE = "123456782"
IDENTIFICATIE = "ZAAK-2020-0010"


@requests_mock.Mocker()
class RecentlyViewedZakenTests(ESMixin, ClearCachesMixin, APITestCase):
    """
    Test the API response body for recently-viewed endpoint.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = SuperUserFactory.create(
            recently_viewed=[
                {
                    "visited": "2020-12-26T12:00:00+00:00",
                    "bronorganisatie": BRONORGANISATIE,
                    "identificatie": IDENTIFICATIE,
                }
            ]
        )
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        cls.url = reverse(
            "recently-viewed",
        )

    def setUp(self):
        # ensure that we have a user with all permissions
        self.client.force_authenticate(user=self.user)

    @freeze_time("2020-12-26T12:00:00+00:00")
    def test_get_recently_viewed(self, m, *mocks):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            identificatie=IDENTIFICATIE,
            bronorganisatie=BRONORGANISATIE,
        )
        mock_resource_get(m, zaak)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "recentlyViewed": [
                    {
                        "visited": "2020-12-26T12:00:00+00:00",
                        "bronorganisatie": "123456782",
                        "identificatie": "ZAAK-2020-0010",
                    }
                ]
            },
        )

    @freeze_time("2020-12-26T13:00:00+00:00")
    def test_set_recently_viewed(self, m, *mocks):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            identificatie="ZAAK-1234",
            bronorganisatie="1234",
        )
        mock_resource_get(m, zaak)
        response = self.client.patch(self.url, {"zaak": zaak["url"]})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "recentlyViewed": [
                    {
                        "visited": "2020-12-26T13:00:00+00:00",
                        "bronorganisatie": "1234",
                        "identificatie": "ZAAK-1234",
                    },
                    {
                        "visited": "2020-12-26T12:00:00+00:00",
                        "bronorganisatie": "123456782",
                        "identificatie": "ZAAK-2020-0010",
                    },
                ]
            },
        )

    @freeze_time("2020-12-26T13:00:00+00:00")
    def test_cant_find_zaak(self, m, *mocks):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            identificatie="ZAAK-1234",
            bronorganisatie="1234",
        )
        m.get(zaak["url"], status_code=404)
        response = self.client.patch(self.url, {"zaak": zaak["url"]})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


@requests_mock.Mocker()
class RecentlyViewedZakenPermissionTests(ESMixin, ClearCachesMixin, APITestCase):
    """
    Test the API permissions for recently-viewed endpoint.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.user = UserFactory.create(
            recently_viewed=[
                {
                    "visited": "2020-12-26T12:00:00+00:00",
                    "bronorganisatie": BRONORGANISATIE,
                    "identificatie": IDENTIFICATIE,
                }
            ]
        )
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        cls.url = reverse(
            "recently-viewed",
        )

    @freeze_time("2020-12-26T12:00:00+00:00")
    def test_get_patch_recently_viewed_no_permissions(self, m, *mocks):
        self.client.force_authenticate(self.user)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.patch(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @freeze_time("2020-12-26T12:00:00+00:00")
    def test_get_patch_recently_viewed_blueprint_permissions(self, m, *mocks):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            identificatie=IDENTIFICATIE,
            bronorganisatie=BRONORGANISATIE,
        )
        mock_resource_get(m, zaak)

        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=self.user,
            policy={
                "catalogus": "",
                "zaaktype_omschrijving": "",
                "max_va": VertrouwelijkheidsAanduidingen.beperkt_openbaar,
            },
        )

        self.client.force_authenticate(self.user)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.patch(self.url, {"zaak": zaak["url"]})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @freeze_time("2020-12-26T12:00:00+00:00")
    def test_get_patch_recently_viewed_atomic_permissions(self, m, *mocks):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            identificatie=IDENTIFICATIE,
            bronorganisatie=BRONORGANISATIE,
        )
        mock_resource_get(m, zaak)

        AtomicPermissionFactory.create(
            object_url=zaak["url"],
            permission=zaken_inzien.name,
            for_user=self.user,
        )

        self.client.force_authenticate(self.user)

        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.patch(self.url, {"zaak": zaak["url"]})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
