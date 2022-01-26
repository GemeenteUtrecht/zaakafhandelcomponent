from django.urls import reverse

import requests_mock
from furl import furl
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
from zac.core.permissions import zaken_wijzigen
from zac.core.tests.utils import ClearCachesMixin
from zac.tests.utils import mock_resource_get, paginated_response

CATALOGI_ROOT = "http://catalogus.nl/api/v1/"
ZAKEN_ROOT = "http://zaken.nl/api/v1/"
ZAAK_URL = f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950"
ZAAK_EIGENSCHAP_URL = (
    f"{ZAAK_URL}/zaakeigenschappen/829ba774-ffd4-4727-8aa3-bf91db611f77"
)


@requests_mock.Mocker()
class ZaakEigenschappenDetailResponseTests(ClearCachesMixin, APITestCase):
    """
    Test the API response body for zaak-detail endpoint.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = SuperUserFactory.create()

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)

        catalogus_url = (
            f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=catalogus_url,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
        )
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=ZAAK_URL,
            identificatie="ZAAK-2020-0010",
            bronorganisatie="123456782",
            zaaktype=cls.zaaktype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            startdatum="2020-12-25",
            uiterlijkeEinddatumAfdoening="2021-01-04",
        )

        cls.endpoint = f"{reverse('zaak-properties-detail')}?url={ZAAK_EIGENSCHAP_URL}"

    def setUp(self):
        super().setUp()

        # ensure that we have a user with all permissions
        self.client.force_authenticate(user=self.user)

    def test_patch_zaak_eigenschap_tekst(self, m):
        eigenschap = generate_oas_component(
            "ztc",
            "schemas/Eigenschap",
            url=f"{CATALOGI_ROOT}eigenschappen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            zaaktype=self.zaaktype["url"],
            naam="some-property",
            specificatie={
                "groep": "dummy",
                "formaat": "tekst",
                "lengte": "3",
                "kardinaliteit": "1",
                "waardenverzameling": [],
            },
        )
        zaak_eigenschap = generate_oas_component(
            "zrc",
            "schemas/ZaakEigenschap",
            url=ZAAK_EIGENSCHAP_URL,
            zaak=ZAAK_URL,
            eigenschap=eigenschap["url"],
            naam=eigenschap["naam"],
            waarde="old",
        )
        zaak_eigenschap_new = zaak_eigenschap.copy()
        zaak_eigenschap_new.update({"waarde": "new"})

        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.zaak)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, zaak_eigenschap)
        mock_resource_get(m, eigenschap)
        m.patch(ZAAK_EIGENSCHAP_URL, json=zaak_eigenschap_new)

        response = self.client.patch(self.endpoint, data={"value": "new"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertEqual(
            response_data,
            {
                "url": ZAAK_EIGENSCHAP_URL,
                "formaat": "tekst",
                "value": "new",
                "eigenschap": {
                    "url": eigenschap["url"],
                    "naam": "some-property",
                    "toelichting": eigenschap["toelichting"],
                    "specificatie": eigenschap["specificatie"],
                },
            },
        )

        last_request = m.request_history[-1]
        self.assertEqual(last_request.method, "PATCH")
        self.assertEqual(last_request.url, ZAAK_EIGENSCHAP_URL)
        self.assertEqual(last_request.json(), {"waarde": "new"})

    def test_patch_zaak_eigenschap_getal(self, m):
        eigenschap = generate_oas_component(
            "ztc",
            "schemas/Eigenschap",
            url=f"{CATALOGI_ROOT}eigenschappen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            zaaktype=self.zaaktype["url"],
            naam="some-property",
            specificatie={
                "groep": "dummy",
                "formaat": "getal",
                "lengte": "2",
                "kardinaliteit": "1",
                "waardenverzameling": [],
            },
        )
        zaak_eigenschap = generate_oas_component(
            "zrc",
            "schemas/ZaakEigenschap",
            url=ZAAK_EIGENSCHAP_URL,
            zaak=ZAAK_URL,
            eigenschap=eigenschap["url"],
            naam=eigenschap["naam"],
            waarde="10",
        )
        zaak_eigenschap_new = zaak_eigenschap.copy()
        zaak_eigenschap_new.update({"waarde": "20"})

        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.zaak)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, zaak_eigenschap)
        mock_resource_get(m, eigenschap)
        m.patch(ZAAK_EIGENSCHAP_URL, json=zaak_eigenschap_new)

        response = self.client.patch(self.endpoint, data={"value": 20})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertEqual(
            response_data,
            {
                "url": ZAAK_EIGENSCHAP_URL,
                "formaat": "getal",
                "value": "20.00",
                "eigenschap": {
                    "url": eigenschap["url"],
                    "naam": "some-property",
                    "toelichting": eigenschap["toelichting"],
                    "specificatie": eigenschap["specificatie"],
                },
            },
        )

        last_request = m.request_history[-1]
        self.assertEqual(last_request.method, "PATCH")
        self.assertEqual(last_request.url, ZAAK_EIGENSCHAP_URL)
        self.assertEqual(last_request.json(), {"waarde": "20"})

    def test_patch_zaak_eigenschap_datum(self, m):
        eigenschap = generate_oas_component(
            "ztc",
            "schemas/Eigenschap",
            url=f"{CATALOGI_ROOT}eigenschappen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            zaaktype=self.zaaktype["url"],
            naam="some-property",
            specificatie={
                "groep": "dummy",
                "formaat": "datum",
                "lengte": "2",
                "kardinaliteit": "1",
                "waardenverzameling": [],
            },
        )
        zaak_eigenschap = generate_oas_component(
            "zrc",
            "schemas/ZaakEigenschap",
            url=ZAAK_EIGENSCHAP_URL,
            zaak=ZAAK_URL,
            eigenschap=eigenschap["url"],
            naam=eigenschap["naam"],
            waarde="2020-01-01",
        )
        zaak_eigenschap_new = zaak_eigenschap.copy()
        zaak_eigenschap_new.update({"waarde": "2020-02-02"})

        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.zaak)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, zaak_eigenschap)
        mock_resource_get(m, eigenschap)
        m.patch(ZAAK_EIGENSCHAP_URL, json=zaak_eigenschap_new)

        response = self.client.patch(self.endpoint, data={"value": "2020-02-02"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json()
        self.assertEqual(
            response_data,
            {
                "url": ZAAK_EIGENSCHAP_URL,
                "formaat": "datum",
                "value": "2020-02-02",
                "eigenschap": {
                    "url": eigenschap["url"],
                    "naam": "some-property",
                    "toelichting": eigenschap["toelichting"],
                    "specificatie": eigenschap["specificatie"],
                },
            },
        )

        last_request = m.request_history[-1]
        self.assertEqual(last_request.method, "PATCH")
        self.assertEqual(last_request.url, ZAAK_EIGENSCHAP_URL)
        self.assertEqual(last_request.json(), {"waarde": "2020-02-02"})

    def test_patch_zaak_eigenschap_not_found(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        m.get(ZAAK_EIGENSCHAP_URL, text="Not Found", status_code=404)

        response = self.client.patch(self.endpoint, data={"value": "new"})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_zaak_eigenschap_incorrect_format(self, m):
        eigenschap = generate_oas_component(
            "ztc",
            "schemas/Eigenschap",
            url=f"{CATALOGI_ROOT}eigenschappen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            zaaktype=self.zaaktype["url"],
            naam="some-property",
            specificatie={
                "groep": "dummy",
                "formaat": "getal",
                "lengte": "2",
                "kardinaliteit": "1",
                "waardenverzameling": [],
            },
        )
        zaak_eigenschap = generate_oas_component(
            "zrc",
            "schemas/ZaakEigenschap",
            url=ZAAK_EIGENSCHAP_URL,
            zaak=ZAAK_URL,
            eigenschap=eigenschap["url"],
            naam=eigenschap["naam"],
            waarde="10",
        )

        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.zaak)
        mock_resource_get(m, zaak_eigenschap)
        mock_resource_get(m, eigenschap)

        response = self.client.patch(self.endpoint, data={"value": "new"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue("value" in response.json())

    def test_patch_without_url(self, m):
        endpoint = reverse("zaak-properties-detail")

        response = self.client.patch(endpoint, data={"value": "new"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue("url" in response.json())

    def test_create_zaak_eigenschap(self, m):
        eigenschap = generate_oas_component(
            "ztc",
            "schemas/Eigenschap",
            url=f"{CATALOGI_ROOT}eigenschappen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            zaaktype=self.zaaktype["url"],
            naam="some-property",
            specificatie={
                "groep": "dummy",
                "formaat": "getal",
                "lengte": "2",
                "kardinaliteit": "1",
                "waardenverzameling": [],
            },
        )
        zaak_eigenschap = generate_oas_component(
            "zrc",
            "schemas/ZaakEigenschap",
            url=ZAAK_EIGENSCHAP_URL,
            zaak=ZAAK_URL,
            eigenschap=eigenschap["url"],
            naam=eigenschap["naam"],
            waarde="10",
        )

        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.zaak)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, eigenschap)
        eigenschappen_url = furl(CATALOGI_ROOT)
        eigenschappen_url.path.segments += ["eigenschappen"]
        eigenschappen_url.path.normalize()
        eigenschappen_url.query = {"zaaktype": self.zaaktype["url"]}
        m.get(eigenschappen_url.url, json=paginated_response([eigenschap]))

        zei_url = furl(self.zaak["url"])
        zei_url.path.segments += ["zaakeigenschappen"]
        zei_url.path.normalize()

        m.post(zei_url.url, json=zaak_eigenschap, status_code=201)
        response = self.client.post(
            self.endpoint,
            data={
                "zaak_url": ZAAK_URL,
                "naam": zaak_eigenschap["naam"],
                "value": zaak_eigenschap["waarde"],
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.json(),
            {
                "url": "http://zaken.nl/api/v1/zaken/e3f5c6d2-0e49-4293-8428-26139f630950/zaakeigenschappen/829ba774-ffd4-4727-8aa3-bf91db611f77",
                "formaat": "getal",
                "eigenschap": {
                    "url": "http://catalogus.nl/api/v1/eigenschappen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
                    "naam": "some-property",
                    "toelichting": eigenschap["toelichting"],
                    "specificatie": {
                        "groep": "dummy",
                        "formaat": "getal",
                        "lengte": "2",
                        "kardinaliteit": "1",
                        "waardenverzameling": [],
                    },
                },
                "value": "10.00",
            },
        )

    def test_create_zaak_eigenschap_fail_name(self, m):
        eigenschap = generate_oas_component(
            "ztc",
            "schemas/Eigenschap",
            url=f"{CATALOGI_ROOT}eigenschappen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            zaaktype=self.zaaktype["url"],
            naam="some-property",
            specificatie={
                "groep": "dummy",
                "formaat": "getal",
                "lengte": "2",
                "kardinaliteit": "1",
                "waardenverzameling": [],
            },
        )

        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.zaak)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, eigenschap)
        eigenschappen_url = furl(CATALOGI_ROOT)
        eigenschappen_url.path.segments += ["eigenschappen"]
        eigenschappen_url.path.normalize()
        eigenschappen_url.query = {"zaaktype": self.zaaktype["url"]}
        m.get(eigenschappen_url.url, json=paginated_response([eigenschap]))

        response = self.client.post(
            self.endpoint,
            data={
                "zaak_url": ZAAK_URL,
                "naam": "some-other-property",
                "value": "10",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            response.json(),
            {"detail": "EIGENSCHAP with name some-other-property not found."},
        )

    def test_delete_zaak_eigenschap(self, m):
        eigenschap = generate_oas_component(
            "ztc",
            "schemas/Eigenschap",
            url=f"{CATALOGI_ROOT}eigenschappen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            zaaktype=self.zaaktype["url"],
            naam="some-property",
            specificatie={
                "groep": "dummy",
                "formaat": "tekst",
                "lengte": "3",
                "kardinaliteit": "1",
                "waardenverzameling": [],
            },
        )
        zaak_eigenschap = generate_oas_component(
            "zrc",
            "schemas/ZaakEigenschap",
            url=ZAAK_EIGENSCHAP_URL,
            zaak=ZAAK_URL,
            eigenschap=eigenschap["url"],
            naam=eigenschap["naam"],
            waarde="old",
        )

        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.zaak)
        mock_resource_get(m, zaak_eigenschap)
        mock_resource_get(m, eigenschap)
        m.delete(ZAAK_EIGENSCHAP_URL, status_code=204)

        response = self.client.delete(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        last_request = m.request_history[-1]
        self.assertEqual(last_request.method, "DELETE")
        self.assertEqual(last_request.url, ZAAK_EIGENSCHAP_URL)

    def test_delete_zaak_eigenschap_not_found(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        m.get(ZAAK_EIGENSCHAP_URL, text="Not Found", status_code=404)

        response = self.client.delete(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_without_url(self, m):
        endpoint = reverse("zaak-properties-detail")

        response = self.client.delete(endpoint)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue("url" in response.json())


class ZaakPropertiesDetailPermissionTests(ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)

        catalogus_url = (
            f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=catalogus_url,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT1",
        )
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=ZAAK_URL,
            identificatie="ZAAK-2020-0010",
            bronorganisatie="123456782",
            zaaktype=cls.zaaktype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            startdatum="2020-12-25",
            uiterlijkeEinddatumAfdoening="2021-01-04",
        )
        cls.eigenschap = generate_oas_component(
            "ztc",
            "schemas/Eigenschap",
            url=f"{CATALOGI_ROOT}eigenschappen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            zaaktype=cls.zaaktype["url"],
            naam="some-property",
            specificatie={
                "groep": "dummy",
                "formaat": "tekst",
                "lengte": "3",
                "kardinaliteit": "1",
                "waardenverzameling": [],
            },
        )
        cls.zaak_eigenschap = generate_oas_component(
            "zrc",
            "schemas/ZaakEigenschap",
            url=ZAAK_EIGENSCHAP_URL,
            zaak=ZAAK_URL,
            eigenschap=cls.eigenschap["url"],
            naam=cls.eigenschap["naam"],
            waarde="old",
        )
        cls.data = {"value": "new"}

        cls.endpoint = f"{reverse('zaak-properties-detail')}?url={ZAAK_EIGENSCHAP_URL}"

    def test_not_authenticated(self):
        response = self.client.delete(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_no_permissions(self):
        user = UserFactory.create()
        self.client.force_authenticate(user=user)

        response = self.client.patch(self.endpoint, self.data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_patch_other_permission(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.zaak)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.zaak_eigenschap)
        mock_resource_get(m, self.eigenschap)

        user = UserFactory.create()
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_wijzigen.name],
            for_user=user,
            policy={
                "catalogus": self.zaaktype["catalogus"],
                "zaaktype_omschrijving": "ZT2",
                "max_va": VertrouwelijkheidsAanduidingen.beperkt_openbaar,
            },
        )
        self.client.force_authenticate(user=user)

        response = self.client.patch(self.endpoint, self.data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_patch_has_perm(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.zaak)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.eigenschap)
        mock_resource_get(m, self.zaak_eigenschap)
        m.patch(ZAAK_EIGENSCHAP_URL, json=self.zaak_eigenschap)

        user = UserFactory.create()
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_wijzigen.name],
            for_user=user,
            policy={
                "catalogus": self.zaaktype["catalogus"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            },
        )
        self.client.force_authenticate(user=user)

        response = self.client.patch(self.endpoint, self.data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @requests_mock.Mocker()
    def test_delete_other_permisison(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.zaak)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.zaak_eigenschap)
        mock_resource_get(m, self.eigenschap)

        user = UserFactory.create()
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_wijzigen.name],
            for_user=user,
            policy={
                "catalogus": self.zaaktype["catalogus"],
                "zaaktype_omschrijving": "ZT2",
                "max_va": VertrouwelijkheidsAanduidingen.beperkt_openbaar,
            },
        )
        self.client.force_authenticate(user=user)

        response = self.client.delete(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_delete_has_perm(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.zaak)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.eigenschap)
        mock_resource_get(m, self.zaak_eigenschap)
        m.delete(ZAAK_EIGENSCHAP_URL, status_code=204)

        user = UserFactory.create()
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_wijzigen.name],
            for_user=user,
            policy={
                "catalogus": self.zaaktype["catalogus"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            },
        )
        self.client.force_authenticate(user=user)

        response = self.client.delete(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
