import datetime
from unittest.mock import patch

from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse

import requests_mock
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.api_models.constants import (
    RolOmschrijving,
    RolTypes,
    VertrouwelijkheidsAanduidingen,
)
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from zac.accounts.tests.factories import (
    BlueprintPermissionFactory,
    GroupFactory,
    SuperUserFactory,
    UserFactory,
)
from zac.camunda.constants import AssigneeTypeChoices
from zac.contrib.objects.oudbehandelaren.tests.factories import (
    OudbehandelarenObjectFactory,
    OudbehandelarenObjectTypeFactory,
)
from zac.core.models import MetaObjectTypesConfig
from zac.core.permissions import zaken_inzien, zaken_wijzigen
from zac.core.tests.utils import ClearCachesMixin
from zac.tests.compat import generate_oas_component, mock_service_oas_get
from zac.tests.utils import mock_resource_get, paginated_response
from zgw.models.zrc import Zaak

CATALOGI_ROOT = "http://catalogus.nl/api/v1/"
ZAKEN_ROOT = "http://zaken.nl/api/v1/"
CATALOGUS_URL = f"{CATALOGI_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"

OUDBEHANDELAREN_OBJECTTYPE = OudbehandelarenObjectTypeFactory()
OUDBEHANDELAREN_OBJECT = OudbehandelarenObjectFactory()


@requests_mock.Mocker()
class ZaakRolesResponseTests(ClearCachesMixin, APITestCase):
    """
    Test the API response body for Roles endpoint.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = SuperUserFactory.create(first_name="Hello", last_name="Goodbye")

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
            omschrijving="Hoofdbehandelaar",
            omschrijvingGeneriek=RolOmschrijving.behandelaar,
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

    @patch("zac.core.rollen.logger")
    def test_get_zaak_rollen(self, m, mock_logger):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")

        medewerker = generate_oas_component(
            "zrc",
            "schemas/RolMedewerker",
            identificatie="some-username",
            achternaam="Orange",
            voorletters="W.",
            voorvoegselAchternaam="van",
        )

        rol = generate_oas_component(
            "zrc",
            "schemas/Rol",
            zaak=self.zaak["url"],
            betrokkene="",
            betrokkeneType="medewerker",
            roltype=self.roltype["url"],
            betrokkeneIdentificatie=medewerker,
        )
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}",
            json=paginated_response([rol]),
        )
        mock_resource_get(m, self.roltype)
        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        expected = [
            {
                "url": rol["url"],
                "betrokkeneType": "medewerker",
                "betrokkeneTypeDisplay": "Medewerker",
                "omschrijving": rol["omschrijving"],
                "omschrijvingGeneriek": rol["omschrijvingGeneriek"],
                "roltoelichting": rol["roltoelichting"],
                "registratiedatum": rol["registratiedatum"].replace("+00:00", "Z"),
                "name": "W. van Orange",
                "identificatie": "some-username",
                "roltypeOmschrijving": self.roltype["omschrijving"],
            }
        ]
        self.assertEqual(response_data, expected)
        mock_logger.warning.called_once_with(
            "Could not resolve betrokkene_identificatie.identificatie to a user. Reverting to information in betrokkene_identificatie."
        )

    @patch("zac.core.rollen.logger")
    def test_get_zaak_rollen_name_from_user_resolve_assignee(self, m, mock_logger):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")

        medewerker = generate_oas_component(
            "zrc",
            "schemas/RolMedewerker",
            identificatie=f"user:{self.user}",
            achternaam="Orange",
            voorletters="W.",
            voorvoegselAchternaam="van",
        )

        rol = generate_oas_component(
            "zrc",
            "schemas/Rol",
            zaak=self.zaak["url"],
            betrokkene="",
            betrokkeneType="medewerker",
            roltype=self.roltype["url"],
            betrokkeneIdentificatie=medewerker,
        )
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}",
            json=paginated_response([rol]),
        )
        mock_resource_get(m, self.roltype)
        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        expected = [
            {
                "url": rol["url"],
                "betrokkeneType": "medewerker",
                "betrokkeneTypeDisplay": "Medewerker",
                "omschrijving": rol["omschrijving"],
                "omschrijvingGeneriek": rol["omschrijvingGeneriek"],
                "roltoelichting": rol["roltoelichting"],
                "registratiedatum": rol["registratiedatum"].replace("+00:00", "Z"),
                "name": "Hello Goodbye",
                "identificatie": f"user:{self.user}",
                "roltypeOmschrijving": self.roltype["omschrijving"],
            }
        ]
        self.assertEqual(response_data, expected)
        mock_logger.assert_not_called()

    def test_get_zaak_rollen_name_from_group_resolve_assignee(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")

        group = GroupFactory.create(name="some-group")
        medewerker = generate_oas_component(
            "zrc",
            "schemas/RolMedewerker",
            identificatie=f"{AssigneeTypeChoices.group}:{group}",
            achternaam="Orange",
            voorletters="W.",
            voorvoegselAchternaam="van",
        )

        rol = generate_oas_component(
            "zrc",
            "schemas/Rol",
            zaak=self.zaak["url"],
            betrokkene="",
            betrokkeneType="medewerker",
            roltype=self.roltype["url"],
            betrokkeneIdentificatie=medewerker,
        )
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}",
            json=paginated_response([rol]),
        )
        mock_resource_get(m, self.roltype)
        with patch("zac.core.rollen.logger") as mock_logger:
            response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        expected = [
            {
                "url": rol["url"],
                "betrokkeneType": "medewerker",
                "betrokkeneTypeDisplay": "Medewerker",
                "omschrijving": rol["omschrijving"],
                "omschrijvingGeneriek": rol["omschrijvingGeneriek"],
                "roltoelichting": rol["roltoelichting"],
                "registratiedatum": rol["registratiedatum"].replace("+00:00", "Z"),
                "name": "Groep: some-group",
                "identificatie": f"{AssigneeTypeChoices.group}:{group}",
                "roltypeOmschrijving": self.roltype["omschrijving"],
            }
        ]
        self.assertEqual(response_data, expected)
        mock_logger.warning.assert_called_with(
            "Groups should not be set on a ROL. Reverting to group name for now."
        )

    def test_get_rollen_no_roles(self, m):
        with patch("zac.core.api.views.get_rollen", return_value=[]):
            response = self.client.get(self.endpoint)

        self.assertEqual(response.data, [])

    def test_zaak_not_found(self, m):
        with patch("zac.core.api.views.find_zaak", side_effect=ObjectDoesNotExist):
            response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

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
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}", json=paginated_response([])
        )

        rol = generate_oas_component(
            "zrc",
            "schemas/Rol",
            betrokkeneIdentificatie={
                "voorletters": "",
                "achternaam": "",
                "identificatie": f"{AssigneeTypeChoices.user}:{self.user}",
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
                "indicatieMachtiging": "gemachtigde",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            response.json(),
            {
                "betrokkene": "",
                "betrokkeneType": "medewerker",
                "indicatieMachtiging": "gemachtigde",
                "roltoelichting": rol["roltoelichting"],
                "roltype": self.roltype["url"],
                "zaak": self.zaak["url"],
                "url": rol["url"],
                "roltypeOmschrijving": self.roltype["omschrijving"],
                "betrokkeneIdentificatie": {
                    "voorletters": "",
                    "achternaam": "",
                    "identificatie": f"{AssigneeTypeChoices.user}:{self.user}",
                    "voorvoegselAchternaam": "",
                },
            },
        )
        self.assertEqual(
            m.request_history[-1].json(),
            {
                "betrokkene": "",
                "betrokkene_identificatie": {
                    "voorletters": "H.",
                    "achternaam": "Goodbye",
                    "identificatie": f"{AssigneeTypeChoices.user}:{self.user}",
                    "voorvoegsel_achternaam": "",
                },
                "betrokkene_type": "medewerker",
                "indicatie_machtiging": "gemachtigde",
                "roltoelichting": self.roltype["omschrijving"],
                "roltype": self.roltype["url"],
                "zaak": self.zaak["url"],
            },
        )

    @patch("zac.contrib.objects.oudbehandelaren.utils.register_old_behandelaar")
    def test_create_rol_oud_behandelaar_already_exists(
        self, m, patch_register_old_behandelaar
    ):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        mock_resource_get(m, self.zaak)
        mock_resource_get(m, self.zaaktype)

        roltype = generate_oas_component(
            "ztc",
            "schemas/RolType",
            url=f"{CATALOGI_ROOT}roltypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
            omschrijving="Hoofdbehandelaar",
            omschrijvingGeneriek=RolOmschrijving.behandelaar,
        )
        mock_resource_get(m, roltype)
        m.get(
            f"{CATALOGI_ROOT}roltypen?zaaktype={self.zaaktype['url']}",
            json=paginated_response([roltype]),
        )
        user = UserFactory.create(username="some-second-rank-user")
        old_rol = generate_oas_component(
            "zrc",
            "schemas/Rol",
            betrokkeneIdentificatie={
                "voorletters": "",
                "achternaam": "",
                "identificatie": f"{AssigneeTypeChoices.user}:{user}",
                "voorvoegselAchternaam": "",
            },
            betrokkeneType="medewerker",
            roltype=roltype["url"],
            betrokkene="",
            indicatieMachtiging="gemachtigde",
            zaak=self.zaak["url"],
            url=f"{ZAKEN_ROOT}rollen/fb498b0b-e4c7-44f1-8e39-a55d9f55ebb9",
            omschrijvingGeneriek=RolOmschrijving.behandelaar,
            omschrijving="Hoofdbehandelaar",
        )
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}",
            json=paginated_response([old_rol]),
        )
        mock_resource_get(m, old_rol)
        m.delete(old_rol["url"], status_code=204)

        new_rol = generate_oas_component(
            "zrc",
            "schemas/Rol",
            betrokkeneIdentificatie={
                "voorletters": "",
                "achternaam": "",
                "identificatie": f"{AssigneeTypeChoices.user}:{self.user}",
                "voorvoegselAchternaam": "",
            },
            betrokkeneType="medewerker",
            roltype=roltype["url"],
            betrokkene="",
            indicatieMachtiging="gemachtigde",
            zaak=self.zaak["url"],
            url=f"{ZAKEN_ROOT}rollen/fb498b0b-e4c7-44f1-8e39-a55d9f55ebb8",
            omschrijvingGeneriek=RolOmschrijving.behandelaar,
            omschrijving="Hoofdbehandelaar",
        )
        m.post(f"{ZAKEN_ROOT}rollen", json=new_rol, status_code=201)

        response = self.client.post(
            self.endpoint,
            {
                "betrokkeneType": "medewerker",
                "betrokkeneIdentificatie": {"identificatie": self.user.username},
                "roltype": roltype["url"],
                "indicatieMachtiging": "gemachtigde",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Check response
        self.assertEqual(
            response.json(),
            {
                "betrokkene": "",
                "betrokkeneType": "medewerker",
                "indicatieMachtiging": "gemachtigde",
                "roltoelichting": new_rol["roltoelichting"],
                "roltype": roltype["url"],
                "zaak": self.zaak["url"],
                "url": new_rol["url"],
                "roltypeOmschrijving": roltype["omschrijving"],
                "betrokkeneIdentificatie": {
                    "voorletters": "",
                    "achternaam": "",
                    "identificatie": f"{AssigneeTypeChoices.user}:{self.user}",
                    "voorvoegselAchternaam": "",
                },
            },
        )

        # Check create call is made
        self.assertEqual(
            m.request_history[-1].json(),
            {
                "betrokkene": "",
                "betrokkene_identificatie": {
                    "voorletters": "H.",
                    "achternaam": "Goodbye",
                    "identificatie": f"{AssigneeTypeChoices.user}:{self.user}",
                    "voorvoegsel_achternaam": "",
                },
                "betrokkene_type": "medewerker",
                "indicatie_machtiging": "gemachtigde",
                "roltoelichting": roltype["omschrijving"],
                "roltype": roltype["url"],
                "zaak": self.zaak["url"],
            },
        )

        # Check delete call is made
        self.assertEqual(m.request_history[-2].method, "DELETE")
        self.assertEqual(m.request_history[-2].url, old_rol["url"])

        # Check if old behandelaar is patched
        patch_register_old_behandelaar.assert_called_once()

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
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}", json=paginated_response([])
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
                "betrokkeneType": "organisatorische_eenheid",
                "betrokkeneIdentificatie": {},
                "roltype": self.roltype["url"],
                "indicatieMachtiging": "gemachtigde",
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
                "roltoelichting": rol["roltoelichting"],
                "roltype": self.roltype["url"],
                "zaak": self.zaak["url"],
                "url": rol["url"],
                "roltypeOmschrijving": self.roltype["omschrijving"],
            },
        )
        self.assertEqual(
            m.request_history[-1].json(),
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
                    "betrokkeneType": "medewerker",
                    "betrokkeneIdentificatie": {"identificatie": self.user.username},
                    "roltype": self.roltype["url"],
                    "indicatieMachtiging": "gemachtigde",
                },
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "nonFieldErrors",
                    "code": "invalid",
                    "reason": "ROLTYPE {rt} is niet onderdeel van de ROLTYPEs van ZAAKTYPE {zt}.".format(
                        rt=self.roltype["url"], zt=self.zaaktype["url"]
                    ),
                }
            ],
        )

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
                    "betrokkeneType": "medewerker",
                    "betrokkeneIdentificatie": {"identificatie": self.user.username},
                    "roltype": self.roltype["url"],
                    "indicatieMachtiging": "gemachtigde",
                },
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "nonFieldErrors",
                    "code": "invalid",
                    "reason": "`betrokkene` en `betrokkene_type` zijn elkaar uitsluitend.",
                }
            ],
        )

        with patch("zac.core.api.views.create_rol", return_value=[]):
            response = self.client.post(
                self.endpoint,
                {
                    "betrokkene": "http://some-url.com",
                    "betrokkeneType": "",
                    "betrokkeneIdentificatie": {"identificatie": self.user.username},
                    "roltype": self.roltype["url"],
                    "indicatieMachtiging": "gemachtigde",
                },
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "nonFieldErrors",
                    "code": "invalid",
                    "reason": "`betrokkene` en `betrokkene_identificatie` zijn elkaar uitsluitend.",
                }
            ],
        )

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
                    "betrokkeneType": "medewerker",
                    "roltype": self.roltype["url"],
                    "indicatieMachtiging": "gemachtigde",
                },
            )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "betrokkeneIdentificatie",
                    "code": "required",
                    "reason": "Dit veld is vereist.",
                }
            ],
        )

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

    def test_fail_destroy_rol_only_one_behandelaar(self, m):
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
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "url",
                    "code": "invalid",
                    "reason": "Een ZAAK heeft altijd tenminste een ROL met `omschrijving_generiek` dat een `behandelaar` of `initiator` is.",
                }
            ],
        )

    def test_fail_destroy_rol_only_one_initiator(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaaktype)
        rol = generate_oas_component(
            "zrc",
            "schemas/Rol",
            zaak=self.zaak["url"],
            url=f"{ZAKEN_ROOT}rollen/07adaa6a-4d2f-4539-9aaf-19b448c4d444/",
            betrokkeneIdentificatie={"identificatie": self.user.username},
            omschrijvingGeneriek=RolOmschrijving.initiator,
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
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "url",
                    "code": "invalid",
                    "reason": "Een ZAAK heeft altijd tenminste een ROL met `omschrijving_generiek` dat een `behandelaar` of `initiator` is.",
                }
            ],
        )

    @patch("zac.contrib.objects.oudbehandelaren.utils.register_old_behandelaar")
    def test_destroy_rol_one_behandelaar_and_one_initiator(
        self, m, patch_register_old_behandelaar
    ):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaaktype)
        initiator = generate_oas_component(
            "zrc",
            "schemas/Rol",
            zaak=self.zaak["url"],
            url=f"{ZAKEN_ROOT}rollen/07adaa6a-4d2f-4539-9aaf-19b448c4d443/",
            betrokkeneIdentificatie={"identificatie": self.user.username},
            omschrijvingGeneriek=RolOmschrijving.initiator,
        )
        behandelaar = generate_oas_component(
            "zrc",
            "schemas/Rol",
            zaak=self.zaak["url"],
            url=f"{ZAKEN_ROOT}rollen/07adaa6a-4d2f-4539-9aaf-19b448c4d444/",
            betrokkeneIdentificatie={"identificatie": self.user.username},
            omschrijvingGeneriek=RolOmschrijving.behandelaar,
        )
        mock_resource_get(m, initiator)
        mock_resource_get(m, behandelaar)
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}",
            json=paginated_response([initiator, behandelaar]),
        )

        m.delete(initiator["url"], status_code=status.HTTP_204_NO_CONTENT)
        response = self.client.delete(
            self.endpoint + "?url=" + initiator["url"],
        )
        self.assertEqual(response.status_code, 204)
        patch_register_old_behandelaar.assert_called_once()

    @freeze_time("2000-01-01T23:59:59Z")
    @patch("zac.contrib.objects.oudbehandelaren.utils.update_object_record_data")
    def test_destroy_rol_register_old_behandelaar(
        self, m, mock_update_object_record_data
    ):
        meta_config = MetaObjectTypesConfig.get_solo()
        meta_config.oudbehandelaren_objecttype = OUDBEHANDELAREN_OBJECTTYPE["url"]
        meta_config.save()

        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.zaaktype)

        initiator = generate_oas_component(
            "zrc",
            "schemas/Rol",
            zaak=self.zaak["url"],
            url=f"{ZAKEN_ROOT}rollen/07adaa6a-4d2f-4539-9aaf-19b448c4d443/",
            betrokkeneIdentificatie={"identificatie": self.user.username},
            omschrijvingGeneriek=RolOmschrijving.initiator,
            betrokkeneType=RolTypes.medewerker,
        )
        behandelaar = generate_oas_component(
            "zrc",
            "schemas/Rol",
            zaak=self.zaak["url"],
            url=f"{ZAKEN_ROOT}rollen/07adaa6a-4d2f-4539-9aaf-19b448c4d444/",
            betrokkeneIdentificatie={"identificatie": self.user.username},
            omschrijvingGeneriek=RolOmschrijving.behandelaar,
        )
        mock_resource_get(m, initiator)
        mock_resource_get(m, behandelaar)
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}",
            json=paginated_response([initiator, behandelaar]),
        )

        m.delete(initiator["url"], status_code=status.HTTP_204_NO_CONTENT)

        with patch(
            "zac.contrib.objects.oudbehandelaren.utils.fetch_oudbehandelaren_object",
            return_value=OUDBEHANDELAREN_OBJECT,
        ):
            response = self.client.delete(
                self.endpoint + "?url=" + initiator["url"],
            )

        OUDBEHANDELAREN_OBJECT["record"]["data"]["behandelaren"] = [
            {
                "email": self.user.email,
                "ended": datetime.datetime.now().isoformat(),
                "started": initiator["registratiedatum"],
                "username": self.user.username,
            }
        ]
        self.assertEqual(response.status_code, 204)
        mock_update_object_record_data.assert_called_once_with(
            OUDBEHANDELAREN_OBJECT,
            OUDBEHANDELAREN_OBJECT["record"]["data"],
            user=self.user,
        )

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
        self.assertEqual(
            response.json()["invalidParams"],
            [
                {
                    "name": "url",
                    "code": "invalid",
                    "reason": "ROL behoort niet toe aan ZAAK.",
                }
            ],
        )


class ZaakRolesPermissionTests(ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)

        cls.catalogus = generate_oas_component(
            "ztc",
            "schemas/Catalogus",
            url=CATALOGUS_URL,
            domein="DOME",
        )
        cls.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=CATALOGUS_URL,
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
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)

        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}",
            json=paginated_response([]),
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
        mock_resource_get(m, self.catalogus)
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={self.zaaktype['catalogus']}",
            json=paginated_response([self.zaaktype]),
        )
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={self.zaak['url']}",
            json=paginated_response([]),
        )

        user = UserFactory.create()
        # gives them access to the page and zaaktype, but insufficient VA
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=user,
            policy={
                "catalogus": self.catalogus["domein"],
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
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.openbaar,
            },
        )
        response = self.client.post(self.endpoint, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @requests_mock.Mocker()
    def test_has_perm_to_list(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
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
                "catalogus": self.catalogus["domein"],
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
        mock_resource_get(m, self.catalogus)
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
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            },
        )
        self.client.force_authenticate(user=user)

        with patch("zac.core.api.views.create_rol", return_value=None):
            response = self.client.post(
                self.endpoint,
                {
                    "betrokkeneType": "medewerker",
                    "betrokkeneIdentificatie": {"identificatie": user.username},
                    "roltype": self.roltype["url"],
                    "indicatieMachtiging": "gemachtigde",
                },
            )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @requests_mock.Mocker()
    def test_has_permission_to_destroy_rol(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_resource_get(m, self.catalogus)
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
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
            },
        )
        self.client.force_authenticate(user=user)
        response = self.client.delete(
            self.endpoint + "?url=" + rol["url"],
        )
        self.assertEqual(response.status_code, 204)
