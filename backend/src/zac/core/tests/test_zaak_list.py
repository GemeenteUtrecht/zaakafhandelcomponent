from unittest import skip

from django.conf import settings
from django.urls import reverse_lazy

import requests_mock
from django_webtest import TransactionWebTest
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.tests.factories import (
    PermissionDefinitionFactory,
    PermissionSetFactory,
    UserFactory,
)
from zac.contrib.organisatieonderdelen.tests.factories import (
    OrganisatieOnderdeelFactory,
)
from zac.elasticsearch.tests.utils import ESMixin
from zgw.models.zrc import Zaak

from ..permissions import zaken_inzien
from .utils import ClearCachesMixin

CATALOGI_ROOT = "https://api.catalogi.nl/api/v1/"
ZAKEN_ROOT = "https://api.zaken.nl/api/v1/"


@requests_mock.Mocker()
class ZaakListTests(ESMixin, ClearCachesMixin, TransactionWebTest):

    url = reverse_lazy("core:index")

    def setUp(self):
        super().setUp()

        self.user = UserFactory.create()

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)

    def test_login_required(self, m):
        response = self.app.get(self.url)

        self.assertRedirects(response, f"{settings.LOGIN_URL}?next={self.url}")

    def test_list_zaken_no_zaaktype_perms(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        zaaktype = generate_oas_component("ztc", "schemas/ZaakType")
        m.get(
            f"{CATALOGI_ROOT}zaaktypen",
            json={
                "count": 1,
                "previous": None,
                "next": None,
                "results": [zaaktype],
            },
        )
        # gives them access to the page, but no zaaktypen specified -> nothing visible
        PermissionSetFactory.create(
            permissions=[zaken_inzien.name],
            for_user=self.user,
            catalogus="",
            zaaktype_identificaties=[],
            max_va=VertrouwelijkheidsAanduidingen.zeer_geheim,
        )

        response = self.app.get(self.url, user=self.user)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["filter_form"].fields["zaaktypen"].choices,
            [],
        )
        self.assertEqual(response.context["zaken"], [])
        # verify amount of API calls - 1 to fetch the schema, 1 to get the zaaktypen
        self.assertEqual(len(m.request_history), 2)

    def test_list_zaken_perm_one_zaaktype(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")

        # set up catalogi data
        catalogus = f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        zt1 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            catalogus=catalogus,
            url=f"{CATALOGI_ROOT}zaaktypen/d66790b7-8b01-4005-a4ba-8fcf2a60f21d",
            identificatie="ZT1",
            omschrijving="ZT1",
        )
        zt2 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            catalogus=catalogus,
            url=f"{CATALOGI_ROOT}zaaktypen/ce05e9c7-b9cd-42d1-ba0e-e0b3d2001be9",
            identificatie="ZT2",
            omschrijving="ZT2",
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktypen",
            json={
                "count": 2,
                "previous": None,
                "next": None,
                "results": [zt1, zt2],
            },
        )
        # set up user permissions
        PermissionSetFactory.create(
            permissions=[zaken_inzien.name],
            for_user=self.user,
            catalogus=catalogus,
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.zeer_geheim,
        )
        PermissionDefinitionFactory.create(
            object_url="",
            permission=zaken_inzien.name,
            for_user=self.user,
            policy={
                "catalogus": catalogus,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.zeer_geheim,
            },
        )
        # set up zaken API data
        zaak1 = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
            zaaktype=zt1["url"],
            vertrouwelijkheidaanduiding=zt1["vertrouwelijkheidaanduiding"],
        )
        zaak2 = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/ce05e9c7-b9cd-42d1-ba0e-e0b3d2001be9",
            zaaktype=zt2["url"],
            vertrouwelijkheidaanduiding=zt1["vertrouwelijkheidaanduiding"],
        )
        zaak1_model = factory(Zaak, zaak1)
        zaak1_model.zaaktype = factory(ZaakType, zt1)
        zaak2_model = factory(Zaak, zaak2)
        zaak2_model.zaaktype = factory(ZaakType, zt2)
        m.get(zaak1["url"], json=zaak1)
        self.create_zaak_document(zaak1_model)
        self.create_zaak_document(zaak2_model)

        response = self.app.get(self.url, user=self.user)

        self.assertEqual(response.status_code, 200)

        zaken = response.context["zaken"]
        self.assertEqual(len(zaken), 1)
        self.assertEqual(zaken[0].url, zaak1["url"])

        zt_choices = response.context["filter_form"].fields["zaaktypen"].choices
        self.assertEqual(len(zt_choices), 1)
        self.assertEqual(zt_choices[0][1][0][0], zt1["url"])

        # verify API calls
        self.assertEqual(
            len(m.request_history),
            5,
        )
        (
            req_ztc_schema,
            req_zaaktypen_catalogus,
            req_zaaktypen,
            req_zrc_schema,
            req_zaak,
        ) = m.request_history
        self.assertEqual(req_zaak.url, zaak1["url"])

    def test_list_zaken_filter_out_max_va(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        # set up catalogi data
        catalogus = f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            catalogus=catalogus,
            url=f"{CATALOGI_ROOT}zaaktypen/d66790b7-8b01-4005-a4ba-8fcf2a60f21d",
            identificatie="ZT1",
            omschrijving="ZT1",
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktypen",
            json={
                "count": 1,
                "previous": None,
                "next": None,
                "results": [zaaktype],
            },
        )
        # set up user permissions
        PermissionSetFactory.create(
            permissions=[zaken_inzien.name],
            for_user=self.user,
            catalogus=catalogus,
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.openbaar,
        )
        PermissionDefinitionFactory.create(
            permission=zaken_inzien.name,
            for_user=self.user,
            policy={
                "catalogus": catalogus,
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.openbaar,
            },
        )
        # set up zaken API data
        zaak1 = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
            zaaktype=zaaktype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
        )
        zaak2 = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/d66790b7-8b01-4005-a4ba-8fcf2a60f21d",
            zaaktype=zaaktype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.zeer_geheim,
        )
        zaak1_model = factory(Zaak, zaak1)
        zaak1_model.zaaktype = factory(ZaakType, zaaktype)
        zaak2_model = factory(Zaak, zaak2)
        zaak2_model.zaaktype = factory(ZaakType, zaaktype)
        m.get(zaak1["url"], json=zaak1)
        self.create_zaak_document(zaak1_model)
        self.create_zaak_document(zaak2_model)

        response = self.app.get(self.url, user=self.user)

        zaken = response.context["zaken"]
        self.assertEqual(len(zaken), 1)
        self.assertEqual(zaken[0].identificatie, zaak1["identificatie"])

    def test_list_zaken_filter_zaaktype_superuser(self, m):
        superuser = UserFactory.create(is_superuser=True)
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")

        # set up catalogi data
        catalogus = f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        zt1 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            catalogus=catalogus,
            url=f"{CATALOGI_ROOT}zaaktypen/d66790b7-8b01-4005-a4ba-8fcf2a60f21d",
            identificatie="ZT1",
        )
        zt2 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            catalogus=catalogus,
            url=f"{CATALOGI_ROOT}zaaktypen/ce05e9c7-b9cd-42d1-ba0e-e0b3d2001be9",
            identificatie="ZT2",
        )
        zaak1 = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
            zaaktype=zt1["url"],
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktypen",
            json={
                "count": 2,
                "previous": None,
                "next": None,
                "results": [zt1, zt2],
            },
        )
        m.get(zaak1["url"], json=zaak1)
        zaak1_model = factory(Zaak, zaak1)
        zaak1_model.zaaktype = factory(ZaakType, zt1)
        self.create_zaak_document(zaak1_model)

        response = self.app.get(self.url, {"zaaktypen": zt1["url"]}, user=superuser)

        self.assertEqual(response.status_code, 200)

        zaken = response.context["zaken"]
        self.assertEqual(len(zaken), 1)
        self.assertEqual(zaken[0].url, zaak1["url"])


@skip("OO restriction is deprecated")
@requests_mock.Mocker()
class OORestrictionTests(ESMixin, ClearCachesMixin, TransactionWebTest):
    """
    Test cases for organisatorischeEenheid restrictions in the permission system.
    """

    url = reverse_lazy("core:index")

    def setUp(self):
        super().setUp()

        self.user = UserFactory.create()

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)

        self.oo = OrganisatieOnderdeelFactory.create(slug="OO-test")

    def test_no_oo_restriction(self, m):
        """
        Test getting a zaak list without OO restrictions.
        """
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")

        # set up catalogi data
        catalogus = f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        zt1 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            catalogus=catalogus,
            url=f"{CATALOGI_ROOT}zaaktypen/d66790b7-8b01-4005-a4ba-8fcf2a60f21d",
            identificatie="ZT1",
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktypen",
            json={
                "count": 1,
                "previous": None,
                "next": None,
                "results": [zt1],
            },
        )
        # set up user permissions
        PermissionSetFactory.create(
            permissions=[zaken_inzien.name],
            catalogus=catalogus,
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.zeer_geheim,
            for_user=self.user,
        )
        # set up zaken API data
        # zaak with rol
        zaak1 = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
            zaaktype=zt1["url"],
            vertrouwelijkheidaanduiding=zt1["vertrouwelijkheidaanduiding"],
            identificatie="zaak1",
        )
        # can't use generate_oas_component because of polymorphism
        rol1 = {
            "url": f"{ZAKEN_ROOT}rollen/b80022cf-6084-4cf6-932b-799effdcdb26",
            "zaak": zaak1["url"],
            "betrokkene": None,
            "betrokkeneType": "organisatorische_eenheid",
            "roltype": f"{CATALOGI_ROOT}roltypen/bfd62804-f46c-42e7-a31c-4139b4c661ac",
            "omschrijving": "zaak behandelaar",
            "omschrijvingGeneriek": "behandelaar",
            "roltoelichting": "some description",
            "registratiedatum": "2020-09-01T00:00:00Z",
            "indicatieMachtiging": "",
            "betrokkeneIdentificatie": {
                "identificatie": self.oo.slug,
            },
        }
        # zaak without rol
        zaak2 = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/d66790b7-8b01-4005-a4ba-8fcf2a60f21d",
            zaaktype=zt1["url"],
            vertrouwelijkheidaanduiding=zt1["vertrouwelijkheidaanduiding"],
            identificatie="zaak2",
        )
        m.get(zaak1["url"], json=zaak1)
        m.get(zaak2["url"], json=zaak2)
        self.create_zaak_document(zaak1)
        self.add_rol_to_document(rol1)
        self.create_zaak_document(zaak2)

        response = self.app.get(self.url, user=self.user)

        self.assertEqual(response.status_code, 200)

        zaken = response.context["zaken"]
        self.assertEqual(len(zaken), 2)

        zaken = sorted(zaken, key=lambda zaak: zaak.identificatie)
        self.assertEqual(zaken[0].url, zaak1["url"])
        self.assertEqual(zaken[1].url, zaak2["url"])

    def test_oo_restriction(self, m):
        """
        Test getting a zaak list with OO restrictions.
        """
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")

        # set up catalogi data
        catalogus = f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        zt1 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            catalogus=catalogus,
            url=f"{CATALOGI_ROOT}zaaktypen/d66790b7-8b01-4005-a4ba-8fcf2a60f21d",
            identificatie="ZT1",
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktypen",
            json={
                "count": 1,
                "previous": None,
                "next": None,
                "results": [zt1],
            },
        )
        # set up user permissions
        perm_set = PermissionSetFactory.create(
            permissions=[zaken_inzien.name],
            catalogus=catalogus,
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.zeer_geheim,
            for_user=self.user,
        )
        ap = perm_set.authorizationprofile_set.get()
        ap.oo = self.oo
        ap.save()

        # set up zaken API data
        # zaak with rol
        zaak1 = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
            zaaktype=zt1["url"],
            vertrouwelijkheidaanduiding=zt1["vertrouwelijkheidaanduiding"],
            identificatie="zaak1",
        )
        # can't use generate_oas_component because of polymorphism
        rol1 = {
            "url": f"{ZAKEN_ROOT}rollen/b80022cf-6084-4cf6-932b-799effdcdb26",
            "zaak": zaak1["url"],
            "betrokkene": None,
            "betrokkeneType": "organisatorische_eenheid",
            "roltype": f"{CATALOGI_ROOT}roltypen/bfd62804-f46c-42e7-a31c-4139b4c661ac",
            "omschrijving": "zaak behandelaar",
            "omschrijvingGeneriek": "behandelaar",
            "roltoelichting": "some description",
            "registratiedatum": "2020-09-01T00:00:00Z",
            "indicatieMachtiging": "",
            "betrokkeneIdentificatie": {
                "identificatie": self.oo.slug,
            },
        }
        # zaak without rol
        zaak2 = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/d66790b7-8b01-4005-a4ba-8fcf2a60f21d",
            zaaktype=zt1["url"],
            vertrouwelijkheidaanduiding=zt1["vertrouwelijkheidaanduiding"],
            identificatie="zaak2",
        )
        # zaak with another oo
        zaak3 = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e13e72de-56ba-42b6-be36-5c280e9b30cd",
            zaaktype=zt1["url"],
            vertrouwelijkheidaanduiding=zt1["vertrouwelijkheidaanduiding"],
            identificatie="zaak2",
        )
        rol3 = {
            "url": f"{ZAKEN_ROOT}rollen/d66790b7-8b01-4005-a4ba-8fcf2a60f21d",
            "zaak": zaak3["url"],
            "betrokkene": None,
            "betrokkeneType": "organisatorische_eenheid",
            "roltype": f"{CATALOGI_ROOT}roltypen/bfd62804-f46c-42e7-a31c-4139b4c661ac",
            "omschrijving": "zaak behandelaar",
            "omschrijvingGeneriek": "behandelaar",
            "roltoelichting": "some description",
            "registratiedatum": "2020-09-01T00:00:00Z",
            "indicatieMachtiging": "",
            "betrokkeneIdentificatie": {
                "identificatie": "12345",
            },
        }
        for zaak in [zaak1, zaak2, zaak3]:
            m.get(zaak["url"], json=zaak)
            self.create_zaak_document(zaak)

        self.add_rol_to_document(rol1)
        self.add_rol_to_document(rol3)

        response = self.app.get(self.url, user=self.user)

        self.assertEqual(response.status_code, 200)
        zaken = response.context["zaken"]
        self.assertEqual(len(zaken), 1)
        self.assertEqual(zaken[0].url, zaak1["url"])

    def test_same_perm_set_multiple_ap(self, m):
        """
        Test list data filtering where one AP has OO limitation and the other doesn't.

        As soon as one AP has no OO-restriction, any OO-restrictions are discarded for
        that zaaktype.
        """
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")

        # set up catalogi data
        catalogus = f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
        zt1 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            catalogus=catalogus,
            url=f"{CATALOGI_ROOT}zaaktypen/d66790b7-8b01-4005-a4ba-8fcf2a60f21d",
            identificatie="ZT1",
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktypen",
            json={
                "count": 1,
                "previous": None,
                "next": None,
                "results": [zt1],
            },
        )
        # set up user permissions
        perm_set = PermissionSetFactory.create(
            permissions=[zaken_inzien.name],
            catalogus=catalogus,
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.zeer_geheim,
            for_user=self.user,
        )
        ap = perm_set.authorizationprofile_set.get()
        ap.oo = self.oo
        ap.save()

        ap2 = perm_set.authorizationprofile_set.create(name="second ap", oo=None)
        ap2.userauthorizationprofile_set.create(user=self.user)

        # set up zaken API data
        # zaak without rol
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
            zaaktype=zt1["url"],
            vertrouwelijkheidaanduiding=zt1["vertrouwelijkheidaanduiding"],
        )
        m.get(zaak["url"], json=zaak)
        self.create_zaak_document(zaak)

        response = self.app.get(self.url, user=self.user)

        self.assertEqual(response.status_code, 200)

        zaken = response.context["zaken"]
        self.assertEqual(len(zaken), 1)
        self.assertEqual(zaken[0].url, zaak["url"])
