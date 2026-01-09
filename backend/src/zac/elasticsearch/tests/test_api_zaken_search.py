import datetime
from unittest.mock import patch

from django.conf import settings
from django.urls import reverse

import requests_mock
from elasticsearch_dsl import Index
from rest_framework import status
from rest_framework.test import APITransactionTestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.api_models.zaken import ZaakObject
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from zac.accounts.tests.factories import (
    ApplicationTokenFactory,
    BlueprintPermissionFactory,
    SuperUserFactory,
    UserFactory,
)
from zac.camunda.constants import AssigneeTypeChoices
from zac.core.permissions import zaken_inzien
from zac.core.tests.utils import ClearCachesMixin
from zac.elasticsearch.api import (
    create_zaakobject_document,
    update_eigenschappen_in_zaak_document,
    update_rollen_in_zaak_document,
)
from zac.elasticsearch.tests.utils import ESMixin
from zac.tests.compat import generate_oas_component, mock_service_oas_get
from zac.tests.utils import mock_resource_get, paginated_response
from zgw.models.zrc import Zaak

from ..documents import ZaakObjectDocument

OBJECTS_ROOT = "http://objects.nl/api/v1/"
CATALOGI_ROOT = "http://catalogus.nl/api/v1/"
CATALOGUS_URL = f"{CATALOGI_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
ZAKEN_ROOT = "http://zaken.nl/api/v1/"


@requests_mock.Mocker()
class SearchPermissionTests(ClearCachesMixin, ESMixin, APITransactionTestCase):
    catalogus = generate_oas_component(
        "ztc",
        "schemas/Catalogus",
        url=CATALOGUS_URL,
        domein="DOME",
    )
    zaaktype = generate_oas_component(
        "ztc",
        "schemas/ZaakType",
        url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
        identificatie="ZT1",
        catalogus=CATALOGUS_URL,
        vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
        omschrijving="ZT1",
    )
    zaak = generate_oas_component(
        "zrc",
        "schemas/Zaak",
        url=f"{ZAKEN_ROOT}zaken/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
        zaaktype=zaaktype["url"],
        identificatie="zaak1",
        omschrijving="Some zaak 1",
        vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
        eigenschappen=[],
        resultaat=f"{ZAKEN_ROOT}resultaten/fcc09bc4-3fd5-4ea4-b6fb-b6c79dbcafca",
    )

    @staticmethod
    def clear_index(init=False):
        ESMixin.clear_index(init=init)
        Index(settings.ES_INDEX_ZO).delete(ignore=404)

        if init:
            ZaakObjectDocument.init()

    @staticmethod
    def refresh_index():
        ESMixin.refresh_index()
        Index(settings.ES_INDEX_ZO).refresh()

    def setUp(self):
        super().setUp()

        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)

        self.zaak_model = factory(Zaak, self.zaak)
        self.zaak_model.zaaktype = factory(ZaakType, self.zaaktype)

        self.endpoint = reverse("search")
        self.data = {"identificatie": "zaak1"}

    def refresh_es(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        zaak_document = self.create_zaak_document(self.zaak_model)
        zaak_document.zaaktype = self.create_zaaktype_document(self.zaak_model.zaaktype)
        zaak_document.save()
        self.refresh_index()

    def test_not_authenticated(self, m):
        self.refresh_es(m)
        response = self.client.post(self.endpoint, self.data)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_authenticated_no_permissions(self, m):
        self.refresh_es(m)
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_resource_get(m, self.catalogus)
        m.get(
            f"{CATALOGI_ROOT}zaaktypen?catalogus={CATALOGUS_URL}",
            json=paginated_response([self.zaaktype]),
        )

        user = UserFactory.create()
        self.client.force_authenticate(user=user)

        response = self.client.post(self.endpoint, self.data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.json()
        self.assertEqual(results["count"], 0)

    def test_has_perm_but_not_for_zaaktype(self, m):
        self.refresh_es(m)
        zaaktype2 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/741c9d1e-de1c-46c6-9ae0-5696f7994ab6",
            identificatie="ZT2",
            catalogus=CATALOGUS_URL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT2",
        )

        m.get(
            f"{CATALOGI_ROOT}zaaktypen",
            json=paginated_response([self.zaaktype, zaaktype2]),
        )
        user = UserFactory.create()
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=user,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": "ZT2",
                "max_va": VertrouwelijkheidsAanduidingen.beperkt_openbaar,
            },
        )
        self.client.force_authenticate(user=user)

        response = self.client.post(self.endpoint, self.data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.json()
        self.assertEqual(results["count"], 0)

    def test_is_superuser(self, m):
        self.refresh_es(m)
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        m.get(f"{CATALOGI_ROOT}zaaktypen", json=paginated_response([self.zaaktype]))
        mock_resource_get(m, self.zaak)

        user = SuperUserFactory.create()
        self.client.force_authenticate(user=user)

        response = self.client.post(self.endpoint, self.data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.json()
        self.assertEqual(results["count"], 1)

    def test_token_auth(self, m):
        self.refresh_es(m)
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        m.get(f"{CATALOGI_ROOT}zaaktypen", json=paginated_response([self.zaaktype]))
        mock_resource_get(m, self.zaak)

        token = ApplicationTokenFactory.create()
        response = self.client.post(
            self.endpoint,
            self.data,
            HTTP_AUTHORIZATION="ApplicationToken " + token.token,
        )
        self.assertEqual(response.status_code, 200)

    def test_token_auth_perms(self, m):
        self.refresh_es(m)
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        m.get(f"{CATALOGI_ROOT}zaaktypen", json=paginated_response([self.zaaktype]))
        mock_resource_get(m, self.zaak)

        token = ApplicationTokenFactory.create()
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_application=token,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.openbaar,
            },
        )

        response = self.client.post(
            self.endpoint,
            self.data,
            HTTP_AUTHORIZATION="ApplicationToken " + token.token,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.json()
        self.assertEqual(results["count"], 1)

    def test_token_auth_perms(self, m):
        self.refresh_es(m)
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        m.get(f"{CATALOGI_ROOT}zaaktypen", json=paginated_response([self.zaaktype]))
        mock_resource_get(m, self.zaak)

        token = ApplicationTokenFactory.create()
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_application=token,
            policy={
                "catalogus": self.catalogus["domein"],
                "zaaktype_omschrijving": "ZT1",
                "max_va": VertrouwelijkheidsAanduidingen.openbaar,
            },
        )

        response = self.client.post(
            self.endpoint,
            self.data,
            HTTP_AUTHORIZATION="ApplicationToken " + token.token,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.json()
        self.assertEqual(results["count"], 1)

    def test_has_perms(self, m):
        self.refresh_es(m)
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        m.get(f"{CATALOGI_ROOT}zaaktypen", json=paginated_response([self.zaaktype]))
        mock_resource_get(m, self.zaak)

        user = UserFactory.create()
        # todo remove after auth refactoring
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

        response = self.client.post(self.endpoint, self.data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.json()
        self.assertEqual(results["count"], 1)


@requests_mock.Mocker()
class SearchResponseTests(ClearCachesMixin, ESMixin, APITransactionTestCase):
    @staticmethod
    def clear_index(init=False):
        ESMixin.clear_index(init=init)
        Index(settings.ES_INDEX_ZO).delete(ignore=404)

        if init:
            ZaakObjectDocument.init()

    @staticmethod
    def refresh_index():
        ESMixin.refresh_index()
        Index(settings.ES_INDEX_ZO).refresh()

    def setUp(self):
        super().setUp()

        # ensure that we have a user with all permissions
        self.user = SuperUserFactory.create()
        self.client.force_authenticate(user=self.user)

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)

        self.endpoint = reverse("search")

    def test_search(self, m):
        # this tests subtests all the different search cases
        # as recreating the ES index for every single scenario
        # costs a lot of time

        # set up catalogi api data
        catalogus = generate_oas_component(
            "ztc",
            "schemas/Catalogus",
            url=CATALOGUS_URL,
            domein="DOME",
        )
        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="1",
            catalogus=CATALOGUS_URL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT1",
        )
        zaaktype_old = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d61",
            identificatie="1",
            catalogus=CATALOGUS_URL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT1_old",
        )
        zaaktype_2 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d62",
            identificatie="2",
            catalogus=CATALOGUS_URL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT2",
        )
        eigenschap = generate_oas_component(
            "ztc",
            "schemas/Eigenschap",
            zaaktype=zaaktype["url"],
            naam="some-property",
            specificatie={
                "groep": "dummy",
                "formaat": "tekst",
                "lengte": "10",
                "kardinaliteit": "1",
                "waardenverzameling": [],
            },
        )
        # set up zaken API data

        ## ZAKEN
        zaak1 = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
            zaaktype=zaaktype["url"],
            identificatie="zaak1",
            omschrijving="Some zaak 1",
            eigenschappen=[],
            resultaat=f"{ZAKEN_ROOT}resultaten/fcc09bc4-3fd5-4ea4-b6fb-b6c79dbcafca",
            bronorganisatie="123456789",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.confidentieel,
            zaakgeometrie={"type": "Point", "coordinates": [4.4683077, 51.9236739]},
        )
        zaak2 = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/d66790b7-8b01-4005-a4ba-8fcf2a60f21d",
            zaaktype=zaaktype_2["url"],
            identificatie="zaak2",
            omschrijving="Other zaak 2",
            eigenschappen=[],
            resultaat=f"{ZAKEN_ROOT}resultaten/f16ce6e3-f6b3-42f9-9c2c-4b6a05f4d7a1",
            zaakgeometrie={"type": "Point", "coordinates": [4, 51]},
        )
        zaak3 = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/d66790b7-8b01-4005-a4ba-8fcf2a60f21e",
            zaaktype=zaaktype_old["url"],
            identificatie="zaak3",
            omschrijving="Other zaak 3",
            eigenschappen=[],
            resultaat=f"{ZAKEN_ROOT}resultaten/f16ce6e3-f6b3-42f9-9c2c-4b6a05f4d7a1",
        )
        zaak4 = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/d66790b7-8b01-4005-a4ba-8fcf2a60f21f",
            zaaktype=zaaktype_old["url"],
            identificatie="zaak4",
            omschrijving="Een zaak met een hele lange beschrijving waar ik op wil zoeken margrietstraat 151515",
            eigenschappen=[],
            resultaat=f"{ZAKEN_ROOT}resultaten/f16ce6e3-f6b3-42f9-9c2c-4b6a05f4d7a1",
        )

        ## ZAAKEIGENSCHAPPEN
        zaak1_eigenschap_1 = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{zaak1['url']}/eigenschappen/1b2b6aa8-bb41-4168-9c07-f586294f008a",
            zaak=zaak1["url"],
            eigenschap=eigenschap["url"],
            naam="Buurt",
            waarde="Leidsche Rijn",
        )
        zaak1_eigenschap_2 = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{zaak1['url']}/eigenschappen/3c008fe4-2aa4-46dc-9bf2-a4590f25c865",
            zaak=zaak1["url"],
            eigenschap=eigenschap["url"],
            naam="Adres",
            waarde="Leidsche Rijn",
        )
        zaak1["eigenschappen"] = [zaak1_eigenschap_1["url"], zaak1_eigenschap_2["url"]]

        ## ZAAKOBJECTEN
        zaakobject = {
            "url": f"{ZAKEN_ROOT}zaakobjecten/4abe87ea-3670-42c8-afc7-5e9fb071971d",
            "object": f"{OBJECTS_ROOT}objects/aa44d251-0ddc-4bf2-b114-00a5ce1925d1",
            "zaak": zaak1["url"],
            "object_type": "",
            "object_type_overige": "",
            "relatieomschrijving": "",
            "object_identificatie": {},
        }

        ## ZAAKROLLEN

        roltype = generate_oas_component(
            "ztc",
            "schemas/RolType",
            url=f"{CATALOGI_ROOT}roltypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
        )
        medewerker = generate_oas_component(
            "zrc",
            "schemas/RolMedewerker",
            identificatie=f"{AssigneeTypeChoices.user}:some-username",
            achternaam="Orange",
            voorletters="W.",
            voorvoegselAchternaam="van",
        )
        rol1 = generate_oas_component(
            "zrc",
            "schemas/Rol",
            zaak=zaak1["url"],
            betrokkene="",
            betrokkeneType="medewerker",
            roltype=roltype["url"],
            betrokkeneIdentificatie=medewerker,
            omschrijvingGeneriek="behandelaar",
        )
        rol2 = generate_oas_component(
            "zrc",
            "schemas/Rol",
            zaak=zaak2["url"],
            betrokkene="",
            betrokkeneType="medewerker",
            roltype=roltype["url"],
            betrokkeneIdentificatie=medewerker,
            omschrijvingGeneriek="initiator",
        )

        medewerker2 = generate_oas_component(
            "zrc",
            "schemas/RolMedewerker",
            identificatie=f"{AssigneeTypeChoices.user}:fred",
            achternaam="Orange",
            voorletters="W.",
            voorvoegselAchternaam="van",
        )
        rol3 = generate_oas_component(
            "zrc",
            "schemas/Rol",
            zaak=zaak3["url"],
            betrokkene="",
            betrokkeneType="medewerker",
            roltype=roltype["url"],
            betrokkeneIdentificatie=medewerker2,
            omschrijvingGeneriek="initiator",
        )

        # mock requests
        # mock services
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")

        # mock external api objects
        # mock catalogi objects
        mock_resource_get(m, catalogus)
        m.get(
            f"{CATALOGI_ROOT}zaaktypen",
            json=paginated_response([zaaktype, zaaktype_old, zaaktype_2]),
        )
        m.get(
            f"{CATALOGI_ROOT}eigenschappen?zaaktype={zaaktype['url']}",
            json=paginated_response([eigenschap]),
        )

        # Mock zaken objects
        mock_resource_get(m, zaak1)
        mock_resource_get(m, zaak2)
        mock_resource_get(m, zaak3)
        mock_resource_get(m, zaak4)

        # Mock zaakeigenschappen
        m.get(
            f"{zaak1['url']}/zaakeigenschappen",
            json=[zaak1_eigenschap_1, zaak1_eigenschap_2],
        )
        m.get(f"{zaak2['url']}/zaakeigenschappen", json=[])
        m.get(f"{zaak3['url']}/zaakeigenschappen", json=[])
        m.get(f"{zaak4['url']}/zaakeigenschappen", json=[])

        # mock zaakobjecten
        m.get(
            f"{ZAKEN_ROOT}zaakobjecten?zaak={zaak1['url']}",
            json=paginated_response([zaakobject]),
        )
        m.get(
            f"{ZAKEN_ROOT}zaakobjecten?zaak={zaak2['url']}",
            json=paginated_response([]),
        )
        m.get(
            f"{ZAKEN_ROOT}zaakobjecten?zaak={zaak3['url']}",
            json=paginated_response([]),
        )
        m.get(
            f"{ZAKEN_ROOT}zaakobjecten?zaak={zaak4['url']}",
            json=paginated_response([]),
        )

        # Mock zaak rollen en roltypes
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={zaak1['url']}",
            json=paginated_response([rol1]),
        )
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={zaak2['url']}",
            json=paginated_response([rol2]),
        )
        m.get(
            f"{ZAKEN_ROOT}rollen?zaak={zaak3['url']}",
            json=paginated_response([rol3]),
        )
        mock_resource_get(m, roltype)

        # index documents in es
        zaak1_model = factory(Zaak, zaak1)
        zaak1_model.deadline = datetime.date(2020, 1, 1)
        zaak1_model.zaaktype = factory(ZaakType, zaaktype)
        zaak1_document = self.create_zaak_document(zaak1_model)
        zaak1_document.zaaktype = self.create_zaaktype_document(zaak1_model.zaaktype)
        zaak1_document.save()
        update_eigenschappen_in_zaak_document(zaak1_model)
        update_rollen_in_zaak_document(zaak1_model)
        zo = create_zaakobject_document(factory(ZaakObject, zaakobject))
        zo.save()

        zaak2_model = factory(Zaak, zaak2)
        zaak2_model.deadline = datetime.date(2020, 1, 2)
        zaak2_model.zaaktype = factory(ZaakType, zaaktype_2)
        zaak2_document = self.create_zaak_document(zaak2_model)
        zaak2_document.zaaktype = self.create_zaaktype_document(zaak2_model.zaaktype)
        zaak2_document.save()
        update_rollen_in_zaak_document(zaak2_model)

        zaak3_model = factory(Zaak, zaak3)
        zaak3_model.deadline = datetime.date(2020, 1, 3)
        zaak3_model.zaaktype = factory(ZaakType, zaaktype_old)
        zaak3_document = self.create_zaak_document(zaak3_model)
        zaak3_document.zaaktype = self.create_zaaktype_document(zaak3_model.zaaktype)
        zaak3_document.save()
        update_rollen_in_zaak_document(zaak3_model)

        zaak4_model = factory(Zaak, zaak4)
        zaak4_model.deadline = datetime.date(2020, 1, 4)
        zaak4_model.zaaktype = factory(ZaakType, zaaktype_old)
        zaak4_document = self.create_zaak_document(zaak4_model)
        zaak4_document.zaaktype = self.create_zaaktype_document(zaak4_model.zaaktype)
        zaak4_document.save()
        self.refresh_index()

        with self.subTest("Search without eigenschappen"):
            data = {
                "identificatie": "zaak1",
                "zaaktypen": {
                    "omschrijving": "ZT1",
                    "catalogus": CATALOGUS_URL,
                },
                "omschrijving": "some",
            }

            response = self.client.post(self.endpoint, data=data)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            results = response.json()
            self.assertEqual(results["count"], 1)
            self.assertEqual(results["results"][0]["url"], zaak1["url"])

        with self.subTest("Search on eigenschappen"):
            data = {"eigenschappen": {"Adres": {"value": "Leidsche Rijn"}}}
            response = self.client.post(self.endpoint, data=data)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            results = response.json()
            self.assertEqual(results["count"], 1)
            self.assertEqual(results["results"][0]["url"], zaak1["url"])

        with self.subTest("Search on partial value of eigenschappen"):
            data = {"eigenschappen": {"Adres": {"value": "Leid"}}}
            response = self.client.post(self.endpoint, data=data)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            results = response.json()
            self.assertEqual(results["count"], 1)
            self.assertEqual(results["results"][0]["url"], zaak1["url"])

            data = {"eigenschappen": {"Adres": {"value": "led"}}}
            response = self.client.post(self.endpoint, data=data)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            results = response.json()
            self.assertEqual(results["count"], 0)

        with self.subTest("Search without input"):
            response = self.client.post(self.endpoint)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data["count"], 4)
            self.assertEqual(data["results"][0]["url"], zaak4["url"])
            self.assertEqual(data["results"][1]["url"], zaak3["url"])
            self.assertEqual(data["results"][2]["url"], zaak2["url"])
            self.assertEqual(data["results"][3]["url"], zaak1["url"])

        with self.subTest("Search with ordering"):
            response = self.client.post(self.endpoint + "?ordering=-deadline")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data["count"], 4)
            self.assertEqual(data["results"][0]["url"], zaak4["url"])
            self.assertEqual(data["results"][1]["url"], zaak3["url"])
            self.assertEqual(data["results"][2]["url"], zaak2["url"])
            self.assertEqual(data["results"][3]["url"], zaak1["url"])

            response = self.client.post(self.endpoint + "?ordering=deadline")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data["count"], 4)
            self.assertEqual(data["results"][0]["url"], zaak1["url"])
            self.assertEqual(data["results"][1]["url"], zaak2["url"])
            self.assertEqual(data["results"][2]["url"], zaak3["url"])
            self.assertEqual(data["results"][3]["url"], zaak4["url"])

        with self.subTest("Search on object"):
            data = {"object": zaakobject["object"]}
            response = self.client.post(self.endpoint, data=data)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            data = response.json()
            self.assertEqual(data["count"], 1)
            self.assertEqual(data["results"][0]["url"], zaak1["url"])

        with self.subTest(
            "Search on zaaktype with same identificatie but different omschrijving"
        ):
            data = {"zaaktype": {"catalogus": CATALOGUS_URL, "omschrijving": "ZT1"}}
            response = self.client.post(
                self.endpoint,
                data=data,
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = response.json()
            self.assertEqual(data["count"], 3)
            self.assertEqual(data["results"][2]["url"], zaak1["url"])
            self.assertEqual(data["results"][1]["url"], zaak3["url"])
            self.assertEqual(data["results"][0]["url"], zaak4["url"])

        with self.subTest("Search without eigenschappen"):
            data = {
                "identificatie": "zaak1",
                "zaaktypen": {
                    "omschrijving": "ZT1",
                    "catalogus": CATALOGUS_URL,
                },
                "omschrijving": "some",
            }

            response = self.client.post(self.endpoint, data=data)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            results = response.json()
            self.assertEqual(results["count"], 1)
            self.assertEqual(results["results"][0]["url"], zaak1["url"])

        with self.subTest("Search on a very long omschrijving"):
            data = {
                "omschrijving": "margrietstraat 151515",
            }

            response = self.client.post(self.endpoint, data=data)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            results = response.json()
            self.assertEqual(results["count"], 1)
            self.assertEqual(results["results"][0]["url"], zaak4["url"])

        with self.subTest("Search on a behandelaar"):
            data = {
                "behandelaar": "some-username",
            }

            response = self.client.post(self.endpoint, data=data)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            results = response.json()
            self.assertEqual(results["count"], 2)
            self.assertEqual(results["results"][0]["url"], zaak2["url"])
            self.assertEqual(results["results"][1]["url"], zaak1["url"])

        with self.subTest("Search on another behandelaar"):
            data = {
                "behandelaar": "fred",
            }

            response = self.client.post(self.endpoint, data=data)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            results = response.json()
            self.assertEqual(results["count"], 1)
            self.assertEqual(results["results"][0]["url"], zaak3["url"])

        with self.subTest("Search with empty list of urls"):
            data = {"object": f"{OBJECTS_ROOT}objects/123"}

            response = self.client.post(self.endpoint, data=data)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            results = response.json()
            self.assertEqual(results["count"], 0)
