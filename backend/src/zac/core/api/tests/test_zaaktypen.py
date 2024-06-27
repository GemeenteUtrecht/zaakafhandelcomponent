from datetime import date

from django.urls import reverse

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import (
    BlueprintPermissionFactory,
    SuperUserFactory,
    UserFactory,
)
from zac.core.permissions import zaken_inzien
from zac.core.tests.utils import ClearCachesMixin
from zac.tests.utils import mock_resource_get, paginated_response

CATALOGI_ROOT = "http://catalogus.nl/api/v1/"
CATALOGUS_URL = f"{CATALOGI_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"


@requests_mock.Mocker()
class ZaaktypenPermissiontests(ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)

        cls.catalogus = generate_oas_component(
            "ztc", "schemas/Catalogus", url=CATALOGUS_URL, domein="some-domein"
        )
        cls.zaaktype_1 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=cls.catalogus["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT1",
        )
        cls.zaaktype_2 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/2a51b38d-efc0-4f7e-9b95-a8c2374c1ac0",
            identificatie="ZT2",
            catalogus=cls.catalogus["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT2",
        )

        cls.endpoint = reverse("zaaktypen")

    def test_not_authenticated(self, m):
        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_no_permissions(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        m.get(
            f"{CATALOGI_ROOT}zaaktypen",
            json=paginated_response([self.zaaktype_1, self.zaaktype_2]),
        )
        m.get(
            f"{CATALOGI_ROOT}catalogussen",
            json=paginated_response([self.catalogus]),
        )

        user = UserFactory.create()
        self.client.force_authenticate(user=user)

        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["results"]), 0)

    def test_has_perm_but_not_for_zaaktype(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        m.get(
            f"{CATALOGI_ROOT}zaaktypen",
            json=paginated_response([self.zaaktype_1, self.zaaktype_2]),
        )
        m.get(
            f"{CATALOGI_ROOT}catalogussen",
            json=paginated_response([self.catalogus]),
        )
        user = UserFactory.create()
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=user,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": "ZT3",
                "max_va": VertrouwelijkheidsAanduidingen.beperkt_openbaar,
            },
        )

        self.client.force_authenticate(user=user)

        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["results"]), 0)

    def test_has_perm_for_one_zaaktype(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        m.get(
            f"{CATALOGI_ROOT}zaaktypen",
            json=paginated_response([self.zaaktype_1, self.zaaktype_2]),
        )
        m.get(
            f"{CATALOGI_ROOT}catalogussen",
            json=paginated_response([self.catalogus]),
        )
        user = UserFactory.create()
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=user,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.beperkt_openbaar,
            },
        )
        self.client.force_authenticate(user=user)

        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()["results"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["omschrijving"], "ZT1")

    def test_is_superuser(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        m.get(
            f"{CATALOGI_ROOT}zaaktypen",
            json=paginated_response([self.zaaktype_1, self.zaaktype_2]),
        )
        m.get(
            f"{CATALOGI_ROOT}catalogussen",
            json=paginated_response([self.catalogus]),
        )
        user = SuperUserFactory.create()
        self.client.force_authenticate(user=user)

        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()["results"]
        self.assertEqual(len(data), 2)

    def test_has_all_perms(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        m.get(
            f"{CATALOGI_ROOT}zaaktypen",
            json=paginated_response([self.zaaktype_1, self.zaaktype_2]),
        )
        m.get(
            f"{CATALOGI_ROOT}catalogussen",
            json=paginated_response([self.catalogus]),
        )
        user = UserFactory.create()
        for zaaktype_omschrijving in ["ZT1", "ZT2"]:
            BlueprintPermissionFactory.create(
                role__permissions=[zaken_inzien.name],
                for_user=user,
                policy={
                    "catalogus": self.catalogus["domein"],
                    "zaaktype_omschrijving": zaaktype_omschrijving,
                    "max_va": VertrouwelijkheidsAanduidingen.beperkt_openbaar,
                },
            )
        self.client.force_authenticate(user=user)

        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()["results"]
        self.assertEqual(len(data), 2)


@requests_mock.Mocker()
class ZaaktypenResponseTests(ClearCachesMixin, APITestCase):
    """
    Test the API response body for zaaktypen endpoint.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = SuperUserFactory.create()

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)

        cls.endpoint = reverse("zaaktypen")

    def setUp(self):
        super().setUp()

        # ensure that we have a user with all permissions
        self.client.force_authenticate(user=self.user)

    def test_get_without_aggregation(self, m):
        catalogus = generate_oas_component(
            "ztc", "schemas/Catalogus", url=CATALOGUS_URL, domein="some-domein"
        )
        zaaktype_1 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=catalogus["url"],
            omschrijving="some zaaktype 1",
        )
        zaaktype_2 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/2a51b38d-efc0-4f7e-9b95-a8c2374c1ac0",
            identificatie="ZT2",
            catalogus=catalogus["url"],
            omschrijving="some zaaktype 2",
        )
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen",
            json=paginated_response([zaaktype_1, zaaktype_2]),
        )
        m.get(
            f"{CATALOGI_ROOT}catalogussen",
            json=paginated_response([catalogus]),
        )

        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data["results"]), 2)
        self.assertEqual(
            data,
            {
                "count": 2,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "omschrijving": "some zaaktype 1",
                        "catalogus": {"domein": "some-domein", "url": CATALOGUS_URL},
                        "identificatie": "ZT1",
                        "url": f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
                    },
                    {
                        "omschrijving": "some zaaktype 2",
                        "catalogus": {"domein": "some-domein", "url": CATALOGUS_URL},
                        "identificatie": "ZT2",
                        "url": f"{CATALOGI_ROOT}zaaktypen/2a51b38d-efc0-4f7e-9b95-a8c2374c1ac0",
                    },
                ],
            },
        )

    def test_get_with_aggregation(self, m):
        catalogus = generate_oas_component(
            "ztc", "schemas/Catalogus", url=CATALOGUS_URL, domein="some-domein"
        )
        zaaktype_v1 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT",
            catalogus=catalogus["url"],
            omschrijving="some zaaktype",
            versiedatum="2020-01-01",
        )
        zaaktype_v2 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/2a51b38d-efc0-4f7e-9b95-a8c2374c1ac0",
            identificatie="ZT",
            catalogus=catalogus["url"],
            omschrijving="some zaaktype",
            versiedatum="2020-01-02",
        )
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen",
            json=paginated_response([zaaktype_v1, zaaktype_v2]),
        )
        m.get(
            f"{CATALOGI_ROOT}catalogussen",
            json=paginated_response([catalogus]),
        )

        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(
            data,
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "omschrijving": "some zaaktype",
                        "catalogus": {"domein": "some-domein", "url": CATALOGUS_URL},
                        "identificatie": "ZT",
                        "url": f"{CATALOGI_ROOT}zaaktypen/2a51b38d-efc0-4f7e-9b95-a8c2374c1ac0",
                    },
                ],
            },
        )

    def test_get_with_filter_q(self, m):
        catalogus = generate_oas_component(
            "ztc", "schemas/Catalogus", url=CATALOGUS_URL, domein="some-domein"
        )
        zaaktype_1 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=CATALOGUS_URL,
            omschrijving="some zaaktype 1",
        )
        zaaktype_2 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/2a51b38d-efc0-4f7e-9b95-a8c2374c1ac0",
            identificatie="ZT2",
            catalogus=CATALOGUS_URL,
            omschrijving="some zaaktype 2",
        )
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen",
            json=paginated_response([zaaktype_1, zaaktype_2]),
        )
        m.get(
            f"{CATALOGI_ROOT}catalogussen",
            json=paginated_response([catalogus]),
        )

        response = self.client.get(self.endpoint, {"q": "ZAAKTYPE 1"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "omschrijving": "some zaaktype 1",
                        "catalogus": {"domein": "some-domein", "url": CATALOGUS_URL},
                        "identificatie": "ZT1",
                        "url": f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
                    },
                ],
            },
        )

    def test_get_with_filter_domein(self, m):
        catalogus = generate_oas_component(
            "ztc", "schemas/Catalogus", url=CATALOGUS_URL, domein="some-domein"
        )
        zaaktype_1 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=CATALOGUS_URL,
            omschrijving="some zaaktype 1",
        )
        catalogus_2 = generate_oas_component(
            "ztc",
            "schemas/Catalogus",
            url=f"{CATALOGI_ROOT}catalogussen/67a31e08-f167-492b-b765-c7b90c472b27",
            domein="some-other-domein",
        )
        zaaktype_2 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/2a51b38d-efc0-4f7e-9b95-a8c2374c1ac0",
            identificatie="ZT2",
            catalogus=catalogus_2["url"],
            omschrijving="some zaaktype 2",
        )
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen",
            json=paginated_response([zaaktype_1, zaaktype_2]),
        )
        m.get(
            f"{CATALOGI_ROOT}catalogussen",
            json=paginated_response([catalogus, catalogus_2]),
        )

        response = self.client.get(self.endpoint, {"domein": "some-domein"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "omschrijving": "some zaaktype 1",
                        "catalogus": {"domein": "some-domein", "url": CATALOGUS_URL},
                        "identificatie": "ZT1",
                        "url": f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
                    },
                ],
            },
        )

    def test_fail_get_with_filter_domein(self, m):
        catalogus = generate_oas_component(
            "ztc", "schemas/Catalogus", url=CATALOGUS_URL, domein="some-domein"
        )
        zaaktype_1 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=CATALOGUS_URL,
            omschrijving="some zaaktype 1",
        )
        catalogus_2 = generate_oas_component(
            "ztc",
            "schemas/Catalogus",
            url=f"{CATALOGI_ROOT}catalogussen/67a31e08-f167-492b-b765-c7b90c472b27",
            domein="some-other-domein",
        )
        zaaktype_2 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/2a51b38d-efc0-4f7e-9b95-a8c2374c1ac0",
            identificatie="ZT2",
            catalogus=catalogus_2["url"],
            omschrijving="some zaaktype 2",
        )
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen",
            json=paginated_response([zaaktype_1, zaaktype_2]),
        )
        m.get(
            f"{CATALOGI_ROOT}catalogussen",
            json=paginated_response([catalogus, catalogus_2]),
        )

        response = self.client.get(self.endpoint, {"domein": "some-random-domein"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "domein",
                    "code": "invalid",
                    "reason": "Kan geen CATALOGUS met `domein`: `some-random-domein` vinden.",
                }
            ],
        )

    def test_get_with_filter_active(self, m):
        catalogus = generate_oas_component(
            "ztc", "schemas/Catalogus", url=CATALOGUS_URL, domein="some-domein"
        )
        zaaktype_1 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=CATALOGUS_URL,
            omschrijving="some zaaktype 1",
            eindeGeldigheid=None,
        )
        zaaktype_2 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/2a51b38d-efc0-4f7e-9b95-a8c2374c1ac0",
            identificatie="ZT2",
            catalogus=CATALOGUS_URL,
            omschrijving="some zaaktype 2",
            eindeGeldigheid="2022-12-12",
        )
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen",
            json=paginated_response([zaaktype_1, zaaktype_2]),
        )
        m.get(
            f"{CATALOGI_ROOT}catalogussen",
            json=paginated_response([catalogus]),
        )

        response = self.client.get(self.endpoint, {"active": True})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                "count": 1,
                "next": None,
                "previous": None,
                "results": [
                    {
                        "omschrijving": "some zaaktype 1",
                        "catalogus": {"domein": "some-domein", "url": CATALOGUS_URL},
                        "identificatie": "ZT1",
                        "url": f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
                    },
                ],
            },
        )
