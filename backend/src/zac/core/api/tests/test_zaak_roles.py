from unittest.mock import patch

from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse

import requests_mock
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.api_models.constants import (
    RolOmschrijving,
    VertrouwelijkheidsAanduidingen,
)
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import (
    BlueprintPermissionFactory,
    SuperUserFactory,
    UserFactory,
)
from zac.contrib.kownsl.models import KownslConfig
from zac.core.permissions import zaken_inzien, zaken_wijzigen
from zac.core.rollen import Rol
from zac.core.tests.utils import ClearCachesMixin
from zac.tests.utils import mock_resource_get, paginated_response
from zgw.models.zrc import Zaak

CATALOGI_ROOT = "http://catalogus.nl/api/v1/"
ZAKEN_ROOT = "http://zaken.nl/api/v1/"
KOWNSL_ROOT = "https://kownsl.nl/"


class ZaakRolesResponseTests(ClearCachesMixin, APITestCase):
    """
    Test the API response body for Roles endpoint.
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
            omschrijving="ZT1",
        )
        cls.roltype = generate_oas_component(
            "ztc",
            "schemas/RolType",
            url=f"{CATALOGI_ROOT}roltypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
        )
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            identificatie="ZAAK-2020-0010",
            bronorganisatie="123456782",
            zaaktype=cls.zaaktype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            startdatum="2020-12-25",
            uiterlijkeEinddatumAfdoening="2021-01-04",
        )

        zaak = factory(Zaak, cls.zaak)
        zaak.zaaktype = factory(ZaakType, cls.zaaktype)
        cls.find_zaak_patcher = patch("zac.core.api.views.find_zaak", return_value=zaak)
        cls.endpoint = reverse(
            "zaak-roles",
            kwargs={
                "bronorganisatie": "123456782",
                "identificatie": "ZAAK-2020-0010",
            },
        )

    def setUp(self):
        super().setUp()

        self.find_zaak_patcher.start()
        self.addCleanup(self.find_zaak_patcher.stop)

        # ensure that we have a user with all permissions
        self.client.force_authenticate(user=self.user)

    def test_get_zaak_rollen(self):
        medewerker = generate_oas_component(
            "zrc",
            "schemas/RolMedewerker",
            identificatie="some-username",
            achternaam="Orange",
            voorletters="W.",
            voorvoegselAchternaam="van",
        )

        _rol = generate_oas_component(
            "zrc",
            "schemas/Rol",
            zaak=self.zaak["url"],
            betrokkene="",
            betrokkeneType="medewerker",
            roltype=f"{CATALOGI_ROOT}roltypen/a28646d7-d0dd-4d6a-a747-7e882fb3e750",
            betrokkeneIdentificatie=medewerker,
        )

        rol = factory(Rol, _rol)

        with patch("zac.core.api.views.get_rollen", return_value=[rol]):
            response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        expected = [
            {
                "url": rol.url,
                "betrokkeneType": "medewerker",
                "betrokkeneTypeDisplay": "Medewerker",
                "omschrijving": rol.omschrijving,
                "omschrijvingGeneriek": rol.omschrijving_generiek,
                "roltoelichting": rol.roltoelichting,
                "registratiedatum": rol.registratiedatum.isoformat().replace(
                    "+00:00", "Z"
                ),
                "name": "W. van Orange",
                "identificatie": "some-username",
            }
        ]
        self.assertEqual(response_data, expected)

    def test_get_rollen_no_roles(self):
        with patch("zac.core.api.views.get_rollen", return_value=[]):
            response = self.client.get(self.endpoint)

        self.assertEqual(response.data, [])

    def test_zaak_not_found(self):
        with patch("zac.core.api.views.find_zaak", side_effect=ObjectDoesNotExist):
            response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @requests_mock.Mocker()
    def test_create_rol(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        mock_resource_get(m, self.zaak)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.roltype)
        m.get(
            f"{CATALOGI_ROOT}roltypen?zaaktype={self.zaaktype['url']}",
            json=paginated_response([self.roltype]),
        )

        rol = generate_oas_component(
            "zrc",
            "schemas/Rol",
            betrokkeneIdentificatie={
                "voorletters": "",
                "achternaam": "",
                "identificatie": f"user:{self.user.username}",
                "voorvoegselAchternaam": "",
            },
            betrokkeneType="medewerker",
            roltype=self.roltype["url"],
            betrokkene="",
            indicatieMachtiging="gemachtigde",
            zaak=self.zaak["url"],
            url=f"{ZAKEN_ROOT}rollen/fb498b0b-e4c7-44f1-8e39-a55d9f55ebb8",
        )
        m.post(f"{ZAKEN_ROOT}rollen", json=rol, status_code=201)
        response = self.client.post(
            self.endpoint,
            {
                "betrokkene_type": "medewerker",
                "betrokkene_identificatie": {"identificatie": self.user.username},
                "roltype": self.roltype["url"],
                "indicatie_machtiging": "gemachtigde",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.json(),
            {
                "betrokkene": "",
                "betrokkeneIdentificatie": {
                    "voorletters": "",
                    "achternaam": "",
                    "identificatie": f"user:{self.user.username}",
                    "voorvoegselAchternaam": "",
                },
                "betrokkeneType": "medewerker",
                "indicatieMachtiging": "gemachtigde",
                "roltoelichting": self.roltype["omschrijving"],
                "roltype": self.roltype["url"],
                "zaak": self.zaak["url"],
                "url": rol["url"],
            },
        )
        self.assertEqual(
            m.last_request.json(),
            {
                "betrokkene": "",
                "betrokkene_identificatie": {
                    "voorletters": "",
                    "achternaam": "",
                    "identificatie": f"user:{self.user.username}",
                    "voorvoegsel_achternaam": "",
                },
                "betrokkene_type": "medewerker",
                "indicatie_machtiging": "gemachtigde",
                "roltoelichting": self.roltype["omschrijving"],
                "roltype": self.roltype["url"],
                "zaak": self.zaak["url"],
            },
        )

    @requests_mock.Mocker()
    def test_create_rol_empty_betrokkene_identificatie(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        mock_resource_get(m, self.zaak)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.roltype)
        m.get(
            f"{CATALOGI_ROOT}roltypen?zaaktype={self.zaaktype['url']}",
            json=paginated_response([self.roltype]),
        )

        rol = generate_oas_component(
            "zrc",
            "schemas/Rol",
            betrokkene="",
            betrokkeneIdentificatie={"identificatie": "some-identificatie"},
            betrokkeneType="organisatorische_eenheid",
            roltype=self.roltype["url"],
            indicatieMachtiging="gemachtigde",
            zaak=self.zaak["url"],
            url=f"{ZAKEN_ROOT}rollen/fb498b0b-e4c7-44f1-8e39-a55d9f55ebb8",
        )
        m.post(f"{ZAKEN_ROOT}rollen", json=rol, status_code=201)
        response = self.client.post(
            self.endpoint,
            {
                "betrokkene_type": "organisatorische_eenheid",
                "betrokkene_identificatie": {},
                "roltype": self.roltype["url"],
                "indicatie_machtiging": "gemachtigde",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.json(),
            {
                "betrokkene": "",
                "betrokkeneIdentificatie": {"identificatie": "some-identificatie"},
                "betrokkeneType": "organisatorische_eenheid",
                "indicatieMachtiging": "gemachtigde",
                "roltoelichting": self.roltype["omschrijving"],
                "roltype": self.roltype["url"],
                "zaak": self.zaak["url"],
                "url": rol["url"],
            },
        )
        self.assertEqual(
            m.last_request.json(),
            {
                "betrokkene": "",
                "betrokkene_identificatie": {},
                "betrokkene_type": "organisatorische_eenheid",
                "indicatie_machtiging": "gemachtigde",
                "roltoelichting": self.roltype["omschrijving"],
                "roltype": self.roltype["url"],
                "zaak": self.zaak["url"],
            },
        )

    @requests_mock.Mocker()
    def test_create_rol_cant_find_roltype(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        mock_resource_get(m, self.zaak)
        mock_resource_get(m, self.zaaktype)
        m.get(
            f"{CATALOGI_ROOT}roltypen?zaaktype={self.zaaktype['url']}",
            json=paginated_response([self.roltype]),
        )
        m.get(self.roltype["url"], status_code=404, json={})

        with patch("zac.core.api.views.create_rol", return_value=[]):
            response = self.client.post(
                self.endpoint,
                {
                    "betrokkene_type": "medewerker",
                    "betrokkene_identificatie": {"identificatie": self.user.username},
                    "roltype": self.roltype["url"],
                    "indicatie_machtiging": "gemachtigde",
                },
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            ["Kan ROLTYPE {rt} niet vinden.".format(rt=self.roltype["url"])],
        )

    @requests_mock.Mocker()
    def test_create_rol_cant_find_roltype_for_zaaktype(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        mock_resource_get(m, self.zaak)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.roltype)
        m.get(
            f"{CATALOGI_ROOT}roltypen?zaaktype={self.zaaktype['url']}",
            json=paginated_response([]),
        )

        with patch("zac.core.api.views.create_rol", return_value=[]):
            response = self.client.post(
                self.endpoint,
                {
                    "betrokkene_type": "medewerker",
                    "betrokkene_identificatie": {"identificatie": self.user.username},
                    "roltype": self.roltype["url"],
                    "indicatie_machtiging": "gemachtigde",
                },
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {
                "nonFieldErrors": [
                    "ROLTYPE {rt} is niet onderdeel van de ROLTYPEs van ZAAKTYPE {zt}.".format(
                        rt=self.roltype["url"], zt=self.zaaktype["url"]
                    )
                ]
            },
        )

    @requests_mock.Mocker()
    def test_create_rol_mutually_exclusive_fields(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        mock_resource_get(m, self.zaak)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.roltype)
        m.get(
            f"{CATALOGI_ROOT}roltypen?zaaktype={self.zaaktype['url']}",
            json=paginated_response([self.roltype]),
        )

        with patch("zac.core.api.views.create_rol", return_value=[]):
            response = self.client.post(
                self.endpoint,
                {
                    "betrokkene": "http://some-betrokkene.com/",
                    "betrokkene_type": "medewerker",
                    "betrokkene_identificatie": {"identificatie": self.user.username},
                    "roltype": self.roltype["url"],
                    "indicatie_machtiging": "gemachtigde",
                },
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {
                "nonFieldErrors": [
                    "`betrokkene` en `betrokkene_type` zijn elkaar uitsluitend."
                ]
            },
        )

        with patch("zac.core.api.views.create_rol", return_value=[]):
            response = self.client.post(
                self.endpoint,
                {
                    "betrokkene": "http://some-url.com",
                    "betrokkene_type": "",
                    "betrokkene_identificatie": {"identificatie": self.user.username},
                    "roltype": self.roltype["url"],
                    "indicatie_machtiging": "gemachtigde",
                },
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {
                "nonFieldErrors": [
                    "`betrokkene` en `betrokkene_identificatie` zijn elkaar uitsluitend."
                ]
            },
        )

    @requests_mock.Mocker()
    def test_create_rol_dependent_fields(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        mock_resource_get(m, self.zaak)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.roltype)
        m.get(
            f"{CATALOGI_ROOT}roltypen?zaaktype={self.zaaktype['url']}",
            json=paginated_response([self.roltype]),
        )

        with patch("zac.core.api.views.create_rol", return_value=[]):
            response = self.client.post(
                self.endpoint,
                {
                    "betrokkene_type": "medewerker",
                    "roltype": self.roltype["url"],
                    "indicatie_machtiging": "gemachtigde",
                },
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {"betrokkeneIdentificatie": ["Dit veld is vereist."]},
        )

    @requests_mock.Mocker()
    def test_destroy_rol(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaaktype)
        rol = generate_oas_component(
            "zrc",
            "schemas/Rol",
            zaak=self.zaak["url"],
            url=f"{ZAKEN_ROOT}rollen/07adaa6a-4d2f-4539-9aaf-19b448c4d444/",
            betrokkene_identificatie={"identificatie": self.user.username},
            omschrijving_generiek=RolOmschrijving.adviseur,
        )
        mock_resource_get(m, rol)
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}",
            json=paginated_response([rol]),
        )

        m.delete(rol["url"], status_code=status.HTTP_204_NO_CONTENT)
        response = self.client.delete(
            self.endpoint + "?url=" + rol["url"],
        )
        self.assertEqual(response.status_code, 204)

    @requests_mock.Mocker()
    def test_fail_destroy_rol(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaaktype)
        rol = generate_oas_component(
            "zrc",
            "schemas/Rol",
            zaak=self.zaak["url"],
            url=f"{ZAKEN_ROOT}rollen/07adaa6a-4d2f-4539-9aaf-19b448c4d444/",
            betrokkene_identificatie={"identificatie": self.user.username},
            omschrijvingGeneriek=RolOmschrijving.behandelaar,
        )
        mock_resource_get(m, rol)
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}",
            json=paginated_response([rol]),
        )

        response = self.client.delete(
            self.endpoint + "?url=" + rol["url"],
        )
        self.assertEqual(response.status_code, 400)

    @requests_mock.Mocker()
    def test_destroy_rol_missing_url(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaaktype)
        rol = generate_oas_component(
            "zrc",
            "schemas/Rol",
            zaak=self.zaak["url"],
            url=f"{ZAKEN_ROOT}rollen/07adaa6a-4d2f-4539-9aaf-19b448c4d444/",
            betrokkene_identificatie={"identificatie": self.user.username},
        )
        mock_resource_get(m, rol)

        m.delete(rol["url"], status_code=status.HTTP_204_NO_CONTENT)
        response = self.client.delete(
            self.endpoint,
        )
        self.assertEqual(response.status_code, 400)

    @requests_mock.Mocker()
    def test_destroy_rol_fail_different_zaak(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaaktype)
        rol = generate_oas_component(
            "zrc",
            "schemas/Rol",
            zaak="http://some-other-zaak.com",
            url=f"{ZAKEN_ROOT}rollen/07adaa6a-4d2f-4539-9aaf-19b448c4d444/",
            betrokkene_identificatie={"identificatie": self.user.username},
        )
        mock_resource_get(m, rol)
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}", json=paginated_response([])
        )

        m.delete(rol["url"], status_code=status.HTTP_204_NO_CONTENT)
        response = self.client.delete(
            self.endpoint + "?url=" + rol["url"],
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"url": ["ROL behoort niet toe aan ZAAK."]})


class ZaakRolesPermissionTests(ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        kownsl = Service.objects.create(api_type=APITypes.orc, api_root=KOWNSL_ROOT)

        config = KownslConfig.get_solo()
        config.service = kownsl
        config.save()

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
        cls.roltype = generate_oas_component(
            "ztc",
            "schemas/RolType",
            url=f"{CATALOGI_ROOT}roltypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
        )
        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            identificatie="ZAAK-2020-0010",
            bronorganisatie="123456782",
            zaaktype=cls.zaaktype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.beperkt_openbaar,
            startdatum="2020-12-25",
            uiterlijkeEinddatumAfdoening="2021-01-04",
        )

        zaak = factory(Zaak, cls.zaak)
        zaak.zaaktype = factory(ZaakType, cls.zaaktype)

        cls.find_zaak_patcher = patch("zac.core.api.views.find_zaak", return_value=zaak)
        cls.get_rollen_patcher = patch("zac.core.api.views.get_rollen", return_value=[])

        cls.endpoint = reverse(
            "zaak-roles",
            kwargs={
                "bronorganisatie": "123456782",
                "identificatie": "ZAAK-2020-0010",
            },
        )

    def setUp(self):
        super().setUp()

        self.find_zaak_patcher.start()
        self.addCleanup(self.find_zaak_patcher.stop)

        self.get_rollen_patcher.start()
        self.addCleanup(self.get_rollen_patcher.stop)

    def test_not_authenticated(self):
        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_no_permissions(self):
        user = UserFactory.create()
        self.client.force_authenticate(user=user)

        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.post(self.endpoint, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_has_perm_but_not_for_zaaktype(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, KOWNSL_ROOT, "kownsl")
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}",
            json=paginated_response([]),
        )
        m.get(
            f"{KOWNSL_ROOT}api/v1/review-requests?for_zaak={self.zaak['url']}",
            json=[],
        )
        # gives them access to the page, but no catalogus specified -> nothing visible
        user = UserFactory.create()
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=user,
            policy={
                "catalogus": "",
                "zaaktype_omschrijving": "",
                "max_va": VertrouwelijkheidsAanduidingen.beperkt_openbaar,
            },
        )
        self.client.force_authenticate(user=user)
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        BlueprintPermissionFactory.create(
            role__permissions=[zaken_wijzigen.name],
            for_user=user,
            policy={
                "catalogus": "",
                "zaaktype_omschrijving": "",
                "max_va": VertrouwelijkheidsAanduidingen.beperkt_openbaar,
            },
        )
        response = self.client.post(self.endpoint, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_has_perm_but_not_for_va(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, KOWNSL_ROOT, "kownsl")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}",
            json=paginated_response([]),
        )
        m.get(
            f"{KOWNSL_ROOT}api/v1/review-requests?for_zaak={self.zaak['url']}",
            json=[],
        )
        user = UserFactory.create()
        # gives them access to the page and zaaktype, but insufficient VA
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=user,
            policy={
                "catalogus": self.zaaktype["catalogus"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.openbaar,
            },
        )
        self.client.force_authenticate(user=user)

        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        BlueprintPermissionFactory.create(
            role__permissions=[zaken_wijzigen.name],
            for_user=user,
            policy={
                "catalogus": self.zaaktype["catalogus"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.openbaar,
            },
        )
        response = self.client.post(self.endpoint, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_has_perm_to_list(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        user = UserFactory.create()
        # gives them access to the page, zaaktype and VA specified -> visible
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=user,
            policy={
                "catalogus": self.zaaktype["catalogus"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            },
        )
        self.client.force_authenticate(user=user)
        response = self.client.get(self.endpoint)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @requests_mock.Mocker()
    def test_has_perm_to_create(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        mock_resource_get(m, self.zaak)
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.roltype)
        m.get(
            f"{CATALOGI_ROOT}roltypen?zaaktype={self.zaaktype['url']}",
            json=paginated_response([self.roltype]),
        )

        user = UserFactory.create()
        # gives them access to the page, zaaktype and VA specified -> visible
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

        with patch("zac.core.api.views.create_rol", return_value=None):
            response = self.client.post(
                self.endpoint,
                {
                    "betrokkene_type": "medewerker",
                    "betrokkene_identificatie": {"identificatie": user.username},
                    "roltype": self.roltype["url"],
                    "indicatie_machtiging": "gemachtigde",
                },
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @requests_mock.Mocker()
    def test_has_permission_to_destroy_rol(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaaktype)
        rol = generate_oas_component(
            "zrc",
            "schemas/Rol",
            zaak=self.zaak["url"],
            url=f"{ZAKEN_ROOT}rollen/07adaa6a-4d2f-4539-9aaf-19b448c4d444/",
            betrokkene_identificatie={"identificatie": "some-username"},
        )
        mock_resource_get(m, rol)
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}",
            json=paginated_response([rol]),
        )
        m.delete(rol["url"], status_code=status.HTTP_204_NO_CONTENT)
        user = UserFactory.create()
        # gives them access to the page, zaaktype and VA specified -> visible
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
        response = self.client.delete(
            self.endpoint + "?url=" + rol["url"],
        )
        self.assertEqual(response.status_code, 204)
