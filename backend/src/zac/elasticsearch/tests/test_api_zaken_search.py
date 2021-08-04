import datetime

from django.urls import reverse

import requests_mock
from rest_framework import status
from rest_framework.test import APITransactionTestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service
from zgw_consumers.test import generate_oas_component, mock_service_oas_get

from zac.accounts.datastructures import VA_ORDER
from zac.accounts.tests.factories import (
    BlueprintPermissionFactory,
    SuperUserFactory,
    UserFactory,
)
from zac.core.permissions import zaken_inzien
from zac.core.tests.utils import ClearCachesMixin
from zac.elasticsearch.api import update_eigenschappen_in_zaak_document
from zac.elasticsearch.tests.utils import ESMixin
from zac.tests.utils import paginated_response
from zgw.models.zrc import Zaak

CATALOGI_ROOT = "http://catalogus.nl/api/v1/"
CATALOGUS_URL = f"{CATALOGI_ROOT}/catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"
ZAKEN_ROOT = "http://zaken.nl/api/v1/"


@requests_mock.Mocker()
class SearchPermissionTests(ClearCachesMixin, ESMixin, APITransactionTestCase):
    def setUp(self):
        super().setUp()

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)

        self.zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=CATALOGUS_URL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT1",
        )
        self.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
            zaaktype=self.zaaktype["url"],
            identificatie="zaak1",
            omschrijving="Some zaak 1",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            eigenschappen=[],
            resultaat=f"{ZAKEN_ROOT}resultaten/fcc09bc4-3fd5-4ea4-b6fb-b6c79dbcafca",
        )
        zaaktype_model = factory(ZaakType, self.zaaktype)
        zaak_model = factory(Zaak, self.zaak)
        zaak_model.zaaktype = zaaktype_model

        self.create_zaak_document(zaak_model)
        self.refresh_index()

        self.endpoint = reverse("search")
        self.data = {"identificatie": "zaak1"}

    def test_not_authenticated(self, m):
        response = self.client.post(self.endpoint, self.data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_no_permissions(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
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
            f"{CATALOGI_ROOT}zaaktypen",
            json=paginated_response([self.zaaktype, zaaktype2]),
        )
        user = UserFactory.create()
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=user,
            policy={
                "catalogus": CATALOGUS_URL,
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
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        m.get(f"{CATALOGI_ROOT}zaaktypen", json=paginated_response([self.zaaktype]))
        m.get(self.zaak["url"], json=self.zaak)

        user = SuperUserFactory.create()
        self.client.force_authenticate(user=user)

        response = self.client.post(self.endpoint, self.data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.json()
        self.assertEqual(results["count"], 1)

    def test_has_perms(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        m.get(f"{CATALOGI_ROOT}zaaktypen", json=paginated_response([self.zaaktype]))
        m.get(self.zaak["url"], json=self.zaak)

        user = UserFactory.create()
        # todo remove after auth refactoring
        BlueprintPermissionFactory.create(
            role__permissions=[zaken_inzien.name],
            for_user=user,
            policy={
                "catalogus": CATALOGUS_URL,
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
    def setUp(self):
        super().setUp()

        # ensure that we have a user with all permissions
        self.user = SuperUserFactory.create()
        self.client.force_authenticate(user=self.user)

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)

        self.endpoint = reverse("search")

    def test_search_without_eigenschappen(self, m):
        # set up catalogi api data
        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=CATALOGUS_URL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT1",
        )
        # set up zaken API data
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
        )
        zaaktype_model = factory(ZaakType, zaaktype)
        zaak1_model = factory(Zaak, zaak1)
        zaak1_model.zaaktype = zaaktype_model
        zaak2 = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/d66790b7-8b01-4005-a4ba-8fcf2a60f21d",
            zaaktype=zaaktype["url"],
            identificatie="zaak2",
            omschrijving="Other zaak 2",
            eigenschappen=[],
            resultaat=f"{ZAKEN_ROOT}resultaten/f16ce6e3-f6b3-42f9-9c2c-4b6a05f4d7a1",
        )
        zaak2_model = factory(Zaak, zaak2)
        zaak2_model.zaaktype = zaaktype_model

        # mock requests
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        m.get(f"{CATALOGI_ROOT}zaaktypen", json=paginated_response([zaaktype]))
        m.get(zaak1["url"], json=zaak1)
        # index documents in es
        self.create_zaak_document(zaak1_model)
        self.create_zaak_document(zaak2_model)
        self.refresh_index()

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

        self.assertEqual(
            results,
            {
                "fields": [
                    "bronorganisatie",
                    "deadline",
                    "einddatum",
                    "identificatie",
                    "omschrijving",
                    "registratiedatum",
                    "rollen.betrokkene_identificatie.identificatie",
                    "rollen.betrokkene_type",
                    "rollen.omschrijving_generiek",
                    "rollen.url",
                    "startdatum",
                    "status.datum_status_gezet",
                    "status.statustoelichting",
                    "status.statustype",
                    "status.url",
                    "toelichting",
                    "url",
                    "va_order",
                    "vertrouwelijkheidaanduiding",
                    "zaaktype.catalogus",
                    "zaaktype.omschrijving",
                    "zaaktype.url",
                ],
                "next": None,
                "previous": None,
                "count": 1,
                "results": [
                    {
                        "url": "http://zaken.nl/api/v1/zaken/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
                        "zaaktype": {
                            "url": "http://catalogus.nl/api/v1/zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
                            "catalogus": "http://catalogus.nl/api/v1//catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd",
                            "omschrijving": "ZT1",
                        },
                        "identificatie": "zaak1",
                        "bronorganisatie": "123456789",
                        "omschrijving": "Some zaak 1",
                        "vertrouwelijkheidaanduiding": "confidentieel",
                        "vaOrder": VA_ORDER["confidentieel"],
                        "rollen": [],
                        "startdatum": zaak1_model.startdatum.isoformat() + "T00:00:00Z",
                        "einddatum": None,
                        "registratiedatum": zaak1_model.registratiedatum.isoformat()
                        + "T00:00:00Z",
                        "deadline": zaak1_model.deadline.isoformat() + "T00:00:00Z",
                        "eigenschappen": [],
                        "status": {
                            "url": None,
                            "statustype": None,
                            "datumStatusGezet": None,
                            "statustoelichting": None,
                        },
                        "toelichting": zaak1_model.toelichting,
                    }
                ],
            },
        )

    def test_search_on_eigenschappen(self, m):
        # set up catalogi api data
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
                "formaat": "tekst",
                "lengte": "10",
                "kardinaliteit": "1",
                "waardenverzameling": [],
            },
        )
        # set up zaken API data
        zaak1 = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
            zaaktype=zaaktype["url"],
            identificatie="zaak1",
            omschrijving="Some zaak 1",
            bronorganisatie="123456789",
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.confidentieel,
        )
        zaak_eigenschap1 = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{zaak1['url']}/eigenschappen/1b2b6aa8-bb41-4168-9c07-f586294f008a",
            zaak=zaak1["url"],
            eigenschap=eigenschap["url"],
            naam="Buurt",
            waarde="Leidsche Rijn",
        )
        zaak1["eigenschappen"] = [zaak_eigenschap1["url"]]
        zaak2 = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/d66790b7-8b01-4005-a4ba-8fcf2a60f21d",
            zaaktype=zaaktype["url"],
            identificatie="zaak2",
            omschrijving="Other zaak 2",
        )
        zaak1_model = factory(Zaak, zaak1)
        zaak1_model.zaaktype = factory(ZaakType, zaaktype)
        zaak_eigenschap2 = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{zaak1['url']}/eigenschappen/3c008fe4-2aa4-46dc-9bf2-a4590f25c865",
            zaak=zaak1["url"],
            eigenschap=eigenschap["url"],
            naam="Adres",
            waarde="Leidsche Rijn",
        )
        zaak2["eigenschappen"] = [zaak_eigenschap2["url"]]
        zaak2_model = factory(Zaak, zaak2)
        zaak2_model.zaaktype = factory(ZaakType, zaaktype)

        # mock requests
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        m.get(f"{CATALOGI_ROOT}zaaktypen", json=paginated_response([zaaktype]))
        m.get(
            f"{CATALOGI_ROOT}eigenschappen?zaaktype={zaaktype['url']}",
            json=paginated_response([eigenschap]),
        )
        m.get(zaak1["url"], json=zaak1)
        m.get(zaak2["url"], json=zaak2)
        m.get(f"{zaak1['url']}/zaakeigenschappen", json=[zaak_eigenschap1])
        m.get(f"{zaak2['url']}/zaakeigenschappen", json=[zaak_eigenschap2])

        # index documents in es
        self.create_zaak_document(zaak1_model)
        self.create_zaak_document(zaak2_model)
        update_eigenschappen_in_zaak_document(zaak1_model)
        update_eigenschappen_in_zaak_document(zaak2_model)
        self.refresh_index()

        input = {"eigenschappen": {"Buurt": {"value": "Leidsche Rijn"}}}

        response = self.client.post(self.endpoint, data=input)

        results = response.json()
        self.assertEqual(
            results,
            {
                "fields": [
                    "bronorganisatie",
                    "deadline",
                    "einddatum",
                    "identificatie",
                    "omschrijving",
                    "registratiedatum",
                    "rollen.betrokkene_identificatie.identificatie",
                    "rollen.betrokkene_type",
                    "rollen.omschrijving_generiek",
                    "rollen.url",
                    "startdatum",
                    "status.datum_status_gezet",
                    "status.statustoelichting",
                    "status.statustype",
                    "status.url",
                    "toelichting",
                    "url",
                    "va_order",
                    "vertrouwelijkheidaanduiding",
                    "zaaktype.catalogus",
                    "zaaktype.omschrijving",
                    "zaaktype.url",
                ],
                "next": None,
                "previous": None,
                "count": 1,
                "results": [
                    {
                        "url": "http://zaken.nl/api/v1/zaken/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
                        "zaaktype": {
                            "url": "http://catalogus.nl/api/v1/zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
                            "catalogus": "http://catalogus.nl/api/v1//catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd",
                            "omschrijving": "ZT1",
                        },
                        "identificatie": "zaak1",
                        "bronorganisatie": "123456789",
                        "omschrijving": "Some zaak 1",
                        "vertrouwelijkheidaanduiding": "confidentieel",
                        "vaOrder": VA_ORDER["confidentieel"],
                        "rollen": [],
                        "startdatum": zaak1_model.startdatum.isoformat() + "T00:00:00Z",
                        "einddatum": None,
                        "registratiedatum": zaak1_model.registratiedatum.isoformat()
                        + "T00:00:00Z",
                        "deadline": zaak1_model.deadline.isoformat() + "T00:00:00Z",
                        "eigenschappen": [],
                        "status": {
                            "url": None,
                            "statustype": None,
                            "datumStatusGezet": None,
                            "statustoelichting": None,
                        },
                        "toelichting": zaak1_model.toelichting,
                    }
                ],
            },
        )

    def test_search_without_input(self, m):
        # set up catalogi api data
        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=CATALOGUS_URL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT1",
        )
        # set up zaken API data
        zaak1 = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
            zaaktype=zaaktype["url"],
            identificatie="zaak1",
            omschrijving="Some zaak 1",
            eigenschappen=[],
            resultaat=f"{ZAKEN_ROOT}resultaten/fcc09bc4-3fd5-4ea4-b6fb-b6c79dbcafca",
        )
        zaak2 = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/d66790b7-8b01-4005-a4ba-8fcf2a60f21d",
            zaaktype=zaaktype["url"],
            identificatie="zaak2",
            omschrijving="Other zaak 2",
            eigenschappen=[],
            resultaat=f"{ZAKEN_ROOT}resultaten/f16ce6e3-f6b3-42f9-9c2c-4b6a05f4d7a1",
        )

        # mock requests
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        m.get(f"{CATALOGI_ROOT}zaaktypen", json=paginated_response([zaaktype]))
        m.get(zaak1["url"], json=zaak1)
        m.get(zaak2["url"], json=zaak2)

        # index documents in es
        zaak1_model = factory(Zaak, zaak1)
        zaak1_model.zaaktype = factory(ZaakType, zaaktype)
        zaak2_model = factory(Zaak, zaak2)
        zaak2_model.zaaktype = factory(ZaakType, zaaktype)
        self.create_zaak_document(zaak1_model)
        self.create_zaak_document(zaak2_model)
        self.refresh_index()

        response = self.client.post(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(data["count"], 2)
        self.assertEqual(data["results"][0]["url"], zaak2["url"])
        self.assertEqual(data["results"][1]["url"], zaak1["url"])

    def test_search_with_ordering(self, m):
        # set up catalogi api data
        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/3e2a1218-e598-4bbe-b520-cb56b0584d60",
            identificatie="ZT1",
            catalogus=CATALOGUS_URL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            omschrijving="ZT1",
        )
        # set up zaken API data
        zaak1 = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
            zaaktype=zaaktype["url"],
            identificatie="zaak1",
            omschrijving="Some zaak 1",
            eigenschappen=[],
            resultaat=f"{ZAKEN_ROOT}resultaten/fcc09bc4-3fd5-4ea4-b6fb-b6c79dbcafca",
        )
        zaak2 = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/d66790b7-8b01-4005-a4ba-8fcf2a60f21d",
            zaaktype=zaaktype["url"],
            identificatie="zaak2",
            omschrijving="Other zaak 2",
            eigenschappen=[],
            resultaat=f"{ZAKEN_ROOT}resultaten/f16ce6e3-f6b3-42f9-9c2c-4b6a05f4d7a1",
        )

        # mock requests
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        m.get(f"{CATALOGI_ROOT}zaaktypen", json=paginated_response([zaaktype]))
        m.get(zaak1["url"], json=zaak1)
        m.get(zaak2["url"], json=zaak2)

        # index documents in es
        zaak1_model = factory(Zaak, zaak1)
        zaak1_model.zaaktype = factory(ZaakType, zaaktype)
        zaak1_model.deadline = datetime.date(2020, 1, 1)
        zaak2_model = factory(Zaak, zaak2)
        zaak2_model.zaaktype = factory(ZaakType, zaaktype)
        zaak2_model.deadline = datetime.date(2020, 1, 2)
        self.create_zaak_document(zaak1_model)
        self.create_zaak_document(zaak2_model)
        self.refresh_index()

        response = self.client.post(self.endpoint + "?ordering=-deadline")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 2)
        self.assertEqual(data["results"][0]["url"], zaak2["url"])
        self.assertEqual(data["results"][1]["url"], zaak1["url"])

        response = self.client.post(self.endpoint + "?ordering=deadline")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["count"], 2)
        self.assertEqual(data["results"][0]["url"], zaak1["url"])
        self.assertEqual(data["results"][1]["url"], zaak2["url"])
