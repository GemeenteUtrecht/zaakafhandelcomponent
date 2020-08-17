from django.urls import reverse_lazy

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.models import APITypes, Service

from zac.accounts.tests.factories import PermissionSetFactory, UserFactory
from zac.core.permissions import zaken_inzien
from zac.core.tests.utils import ClearCachesMixin
from zac.tests.utils import generate_oas_component, mock_service_oas_get

from .factories import ActivityFactory

ZAKEN_ROOT = "https://open-zaak.nl/zaken/api/v1/"
CATALOGI_ROOT = "https://open-zaak.nl/catalogi/api/v1/"


class ReadPermissionTests(ClearCachesMixin, APITestCase):
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
        Service.objects.create(
            label="Catalogi API", api_type=APITypes.ztc, api_root=CATALOGI_ROOT,
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

    @requests_mock.Mocker()
    def test_read_logged_in_zaak_permission(self, m):
        user = UserFactory.create()
        self.client.force_login(user)
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        catalogus = f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            catalogus=catalogus,
            url=f"{CATALOGI_ROOT}zaaktypen/d66790b7-8b01-4005-a4ba-8fcf2a60f21d",
            identificatie="ZT1",
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktypen",
            json={"count": 1, "previous": None, "next": None, "results": [zaaktype],},
        )
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/30a98ef3-bf35-4287-ac9c-fed048619dd7",
            zaaktype=zaaktype["url"],
        )
        m.get(zaak["url"], json=zaak)

        # set up user permissions
        PermissionSetFactory.create(
            permissions=[zaken_inzien.name],
            for_user=user,
            catalogus=catalogus,
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.zeer_geheim,
        )
        # set up test data
        ActivityFactory.create()
        activity = ActivityFactory.create(zaak=zaak["url"])

        response = self.client.get(self.endpoint, {"zaak": zaak["url"]})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        self.assertEqual(response.data[0]["id"], activity.id)
