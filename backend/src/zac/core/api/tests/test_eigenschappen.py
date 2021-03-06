from unittest.mock import patch

from django.urls import reverse

import requests_mock
from rest_framework import status
from rest_framework.test import APITransactionTestCase
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
CATALOGUS_URL = f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"


@requests_mock.Mocker()
class EigenschappenPermissiontests(ClearCachesMixin, APITransactionTestCase):
    def setUp(self):
        super().setUp()

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)

        self.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=CATALOGUS_URL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT1",
        )
        self.eigenschap = generate_oas_component(
            "ztc",
            "schemas/Eigenschap",
            zaaktype=self.zaaktype["url"],
            naam="some-property",
            specificatie={
                "groep": "dummy",
                "formaat": "tekst",
                "lengte": "3",
                "kardinaliteit": "1",
                "waardenverzameling": ["aaa", "bbb"],
            },
        )

        self.endpoint = reverse("eigenschappen")

    def test_not_authenticated(self, m):
        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_no_permissions(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={CATALOGUS_URL}",
            json=paginated_response([self.zaaktype]),
        )

        user = UserFactory.create()
        self.client.force_authenticate(user=user)

        response = self.client.get(
            self.endpoint, {"catalogus": CATALOGUS_URL, "zaaktype_omschrijving": "ZT1"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 0)

    def test_has_perm_but_not_for_zaaktype(self, m):
        zaaktype2 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/741c9d1e-de1c-46c6-9ae0-5696f7994ab6",
            identificatie="ZT2",
            catalogus=CATALOGUS_URL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT2",
        )

        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={CATALOGUS_URL}",
            json=paginated_response([self.zaaktype, zaaktype2]),
        )
        user = UserFactory.create()
        BlueprintPermissionFactory.create(
            permission=zaken_inzien.name,
            for_user=user,
            policy={
                "catalogus": CATALOGUS_URL,
                "zaaktype_omschrijving": "ZT2",
                "max_va": VertrouwelijkheidsAanduidingen.beperkt_openbaar,
            },
        )
        self.client.force_authenticate(user=user)

        response = self.client.get(
            self.endpoint, {"catalogus": CATALOGUS_URL, "zaaktype_omschrijving": "ZT1"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 0)

    def test_is_superuser(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={CATALOGUS_URL}",
            json=paginated_response([self.zaaktype]),
        )
        m.get(
            f"{CATALOGI_ROOT}eigenschappen?zaaktype={self.zaaktype['url']}",
            json=paginated_response([self.eigenschap]),
        )
        user = SuperUserFactory.create()
        self.client.force_authenticate(user=user)

        response = self.client.get(
            self.endpoint, {"catalogus": CATALOGUS_URL, "zaaktype_omschrijving": "ZT1"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(len(data), 1)

    def test_has_perms(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={CATALOGUS_URL}",
            json=paginated_response([self.zaaktype]),
        )
        m.get(
            f"{CATALOGI_ROOT}eigenschappen?zaaktype={self.zaaktype['url']}",
            json=paginated_response([self.eigenschap]),
        )
        user = UserFactory.create()
        BlueprintPermissionFactory.create(
            permission=zaken_inzien.name,
            for_user=user,
            policy={
                "catalogus": CATALOGUS_URL,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.beperkt_openbaar,
            },
        )
        self.client.force_authenticate(user=user)

        response = self.client.get(
            self.endpoint, {"catalogus": CATALOGUS_URL, "zaaktype_omschrijving": "ZT1"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(len(data), 1)


class EigenschappenResponseTests(ClearCachesMixin, APITransactionTestCase):
    def setUp(self):
        super().setUp()

        # ensure that we have a user with all permissions
        self.user = SuperUserFactory.create()
        self.client.force_authenticate(user=self.user)

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)

        self.endpoint = reverse("eigenschappen")

    @requests_mock.Mocker()
    def test_get_eigenschappen_string(self, m):
        zaaktype1 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=CATALOGUS_URL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT1",
        )
        eigenschap1 = generate_oas_component(
            "ztc",
            "schemas/Eigenschap",
            zaaktype=zaaktype1["url"],
            naam="some-property",
            specificatie={
                "groep": "dummy",
                "formaat": "tekst",
                "lengte": "3",
                "kardinaliteit": "1",
                "waardenverzameling": ["aaa", "bbb"],
            },
        )
        zaaktype2 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/741c9d1e-de1c-46c6-9ae0-5696f7994ab6",
            identificatie="ZT2",
            catalogus=CATALOGUS_URL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT2",
        )
        eigenschap2 = generate_oas_component(
            "ztc",
            "schemas/Eigenschap",
            zaaktype=zaaktype2["url"],
            naam="other-property",
            specificatie={
                "groep": "dummy",
                "formaat": "tekst",
                "lengte": "1",
                "kardinaliteit": "1",
                "waardenverzameling": [],
            },
        )

        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, zaaktype1)
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={CATALOGUS_URL}",
            json=paginated_response([zaaktype1, zaaktype2]),
        )
        m.get(
            f"{CATALOGI_ROOT}eigenschappen?zaaktype={zaaktype1['url']}",
            json=paginated_response([eigenschap1]),
        )

        response = self.client.get(
            self.endpoint, {"catalogus": CATALOGUS_URL, "zaaktype_omschrijving": "ZT1"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(
            data,
            [
                {
                    "name": "some-property",
                    "spec": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 3,
                        "enum": ["aaa", "bbb"],
                    },
                }
            ],
        )

    @requests_mock.Mocker()
    def test_get_eigenschappen_number(self, m):
        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=CATALOGUS_URL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT1",
        )
        eigenschap = generate_oas_component(
            "ztc",
            "schemas/Eigenschap",
            zaaktype=zaaktype["url"],
            naam="some-property",
            specificatie={
                "groep": "dummy",
                "formaat": "getal",
                "lengte": "1",
                "kardinaliteit": "1",
                "waardenverzameling": [1, 2],
            },
        )

        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, zaaktype)
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={CATALOGUS_URL}",
            json=paginated_response([zaaktype]),
        )
        m.get(
            f"{CATALOGI_ROOT}eigenschappen?zaaktype={zaaktype['url']}",
            json=paginated_response([eigenschap]),
        )

        response = self.client.get(
            self.endpoint, {"catalogus": CATALOGUS_URL, "zaaktype_omschrijving": "ZT1"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(
            data,
            [
                {
                    "name": "some-property",
                    "spec": {
                        "type": "number",
                        "enum": [1, 2],
                    },
                }
            ],
        )

    def test_get_eigenschappen_without_query_params(self):
        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(),
            {
                "zaaktypeOmschrijving": ["Dit veld is vereist."],
                "catalogus": ["Dit veld is vereist."],
            },
        )

    def test_get_eigenschappen_with_invalid_query_param(self):
        response = self.client.get(
            self.endpoint, {"catalogus": "some-url", "zaaktype_omschrijving": "ZT1"}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), {"catalogus": ["Voer een geldige URL in."]})

    @requests_mock.Mocker()
    def test_get_eigenschappen_with_same_name_and_spec(self, m):
        zaaktype1 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT",
            catalogus=CATALOGUS_URL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT",
        )
        eigenschap1 = generate_oas_component(
            "ztc",
            "schemas/Eigenschap",
            zaaktype=zaaktype1["url"],
            naam="some-property",
            specificatie={
                "groep": "dummy",
                "formaat": "tekst",
                "lengte": "3",
                "kardinaliteit": "1",
                "waardenverzameling": ["aaa", "bbb"],
            },
        )
        zaaktype2 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/741c9d1e-de1c-46c6-9ae0-5696f7994ab6",
            identificatie="ZT",
            catalogus=CATALOGUS_URL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT",
        )
        eigenschap2 = generate_oas_component(
            "ztc",
            "schemas/Eigenschap",
            zaaktype=zaaktype2["url"],
            naam="some-property",
            specificatie={
                "groep": "dummy",
                "formaat": "tekst",
                "lengte": "3",
                "kardinaliteit": "1",
                "waardenverzameling": ["aaa", "bbb"],
            },
        )

        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, zaaktype1)
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={CATALOGUS_URL}",
            json=paginated_response([zaaktype1, zaaktype2]),
        )
        m.get(
            f"{CATALOGI_ROOT}eigenschappen?zaaktype={zaaktype1['url']}",
            json=paginated_response([eigenschap1]),
        )
        m.get(
            f"{CATALOGI_ROOT}eigenschappen?zaaktype={zaaktype2['url']}",
            json=paginated_response([eigenschap2]),
        )

        response = self.client.get(
            self.endpoint, {"catalogus": CATALOGUS_URL, "zaaktype_omschrijving": "ZT"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(
            data,
            [
                {
                    "name": "some-property",
                    "spec": {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 3,
                        "enum": ["aaa", "bbb"],
                    },
                }
            ],
        )

    @patch("zac.core.api.views.logger")
    @requests_mock.Mocker()
    def test_get_eigenschappen_with_same_name_but_different_spec(self, m_logger, m_req):
        zaaktype1 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT",
            catalogus=CATALOGUS_URL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT",
        )
        eigenschap1 = generate_oas_component(
            "ztc",
            "schemas/Eigenschap",
            zaaktype=zaaktype1["url"],
            naam="some-property",
            specificatie={
                "groep": "dummy",
                "formaat": "tekst",
                "lengte": "3",
                "kardinaliteit": "1",
                "waardenverzameling": ["aaa", "bbb"],
            },
        )
        zaaktype2 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/741c9d1e-de1c-46c6-9ae0-5696f7994ab6",
            identificatie="ZT",
            catalogus=CATALOGUS_URL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT",
        )
        eigenschap2 = generate_oas_component(
            "ztc",
            "schemas/Eigenschap",
            zaaktype=zaaktype2["url"],
            naam="some-property",
            specificatie={
                "groep": "dummy",
                "formaat": "tekst",
                "lengte": "1",
                "kardinaliteit": "1",
                "waardenverzameling": [],
            },
        )

        mock_service_oas_get(m_req, CATALOGI_ROOT, "ztc")
        mock_resource_get(m_req, zaaktype1)
        m_req.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={CATALOGUS_URL}",
            json=paginated_response([zaaktype1, zaaktype2]),
        )
        m_req.get(
            f"{CATALOGI_ROOT}eigenschappen?zaaktype={zaaktype1['url']}",
            json=paginated_response([eigenschap1]),
        )
        m_req.get(
            f"{CATALOGI_ROOT}eigenschappen?zaaktype={zaaktype2['url']}",
            json=paginated_response([eigenschap2]),
        )

        response = self.client.get(
            self.endpoint, {"catalogus": CATALOGUS_URL, "zaaktype_omschrijving": "ZT"}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data), 1)
        # can't assert spec since it's value is uncertain
        self.assertEqual(data[0]["name"], "some-property")
        m_logger.warning.assert_called_with(
            "Eigenschappen 'some-property' which belong to zaaktype 'ZT' have different specs"
        )
