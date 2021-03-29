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

from zac.accounts.tests.factories import (
    PermissionSetFactory,
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
        self.create_zaak_document(self.zaak)
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
            f"{CATALOGI_ROOT}zaaktypen",
            json=paginated_response([self.zaaktype, zaaktype2]),
        )
        user = UserFactory.create()
        PermissionSetFactory.create(
            permissions=[zaken_inzien.name],
            for_user=user,
            catalogus=CATALOGUS_URL,
            zaaktype_identificaties=["ZT2"],
            max_va=VertrouwelijkheidsAanduidingen.beperkt_openbaar,
        )
        self.client.force_authenticate(user=user)

        response = self.client.post(self.endpoint, self.data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 0)

    def test_is_superuser(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        m.get(f"{CATALOGI_ROOT}zaaktypen", json=paginated_response([self.zaaktype]))
        m.get(self.zaak["url"], json=self.zaak)

        user = SuperUserFactory.create()
        self.client.force_authenticate(user=user)

        response = self.client.post(self.endpoint, self.data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(len(data), 1)

    def test_has_perms(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        m.get(f"{CATALOGI_ROOT}zaaktypen", json=paginated_response([self.zaaktype]))
        m.get(self.zaak["url"], json=self.zaak)

        user = UserFactory.create()
        PermissionSetFactory.create(
            permissions=[zaken_inzien.name],
            for_user=user,
            catalogus=CATALOGUS_URL,
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.openbaar,
        )
        self.client.force_authenticate(user=user)

        response = self.client.post(self.endpoint, self.data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(len(data), 1)


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
        )
        zaak1_model = factory(Zaak, zaak1)
        zaak1_model.zaaktype = factory(ZaakType, zaaktype)
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

        # index documents in es
        self.create_zaak_document(zaak1)
        self.create_zaak_document(zaak2)
        self.refresh_index()

        data = {
            "identificatie": "zaak1",
            "zaaktype": {
                "omschrijving": "ZT1",
                "catalogus": CATALOGUS_URL,
            },
            "omschrijving": "some",
        }

        response = self.client.post(self.endpoint, data=data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(
            data,
            [
                {
                    "url": zaak1_model.url,
                    "identificatie": "zaak1",
                    "bronorganisatie": zaak1_model.bronorganisatie,
                    "zaaktype": {
                        "url": zaaktype["url"],
                        "catalogus": CATALOGUS_URL,
                        "omschrijving": "ZT1",
                        "versiedatum": zaaktype["versiedatum"],
                    },
                    "omschrijving": "Some zaak 1",
                    "toelichting": zaak1_model.toelichting,
                    "registratiedatum": zaak1_model.registratiedatum.isoformat(),
                    "startdatum": zaak1_model.startdatum.isoformat(),
                    "einddatum": None,
                    "einddatumGepland": zaak1_model.einddatum_gepland,
                    "uiterlijkeEinddatumAfdoening": zaak1_model.uiterlijke_einddatum_afdoening,
                    "vertrouwelijkheidaanduiding": zaak1_model.vertrouwelijkheidaanduiding,
                    "deadline": zaak1_model.deadline.isoformat(),
                    "deadlineProgress": zaak1_model.deadline_progress(),
                    "resultaat": None,
                }
            ],
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
        self.create_zaak_document(zaak1)
        self.create_zaak_document(zaak2)
        update_eigenschappen_in_zaak_document(zaak1_model)
        update_eigenschappen_in_zaak_document(zaak2_model)
        self.refresh_index()

        input = {"eigenschappen": {"Buurt": {"value": "Leidsche Rijn"}}}

        response = self.client.post(self.endpoint, data=input)

        data = response.json()

        self.assertEqual(len(data), 1)
        self.assertEqual(
            data,
            [
                {
                    "url": zaak1_model.url,
                    "identificatie": "zaak1",
                    "bronorganisatie": zaak1_model.bronorganisatie,
                    "zaaktype": {
                        "url": zaaktype["url"],
                        "catalogus": CATALOGUS_URL,
                        "omschrijving": "ZT1",
                        "versiedatum": zaaktype["versiedatum"],
                    },
                    "omschrijving": "Some zaak 1",
                    "toelichting": zaak1_model.toelichting,
                    "registratiedatum": zaak1_model.registratiedatum.isoformat(),
                    "startdatum": zaak1_model.startdatum.isoformat(),
                    "einddatum": None,
                    "einddatumGepland": zaak1_model.einddatum_gepland,
                    "uiterlijkeEinddatumAfdoening": zaak1_model.uiterlijke_einddatum_afdoening,
                    "vertrouwelijkheidaanduiding": zaak1_model.vertrouwelijkheidaanduiding,
                    "deadline": zaak1_model.deadline.isoformat(),
                    "deadlineProgress": zaak1_model.deadline_progress(),
                    "resultaat": None,
                }
            ],
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
        self.create_zaak_document(zaak1)
        self.create_zaak_document(zaak2)
        self.refresh_index()

        response = self.client.post(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()

        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["url"], zaak2["url"])
        self.assertEqual(data[1]["url"], zaak1["url"])
