from unittest.mock import patch

from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse

import requests_mock
from freezegun import freeze_time
from rest_framework import status
from rest_framework.test import APITestCase
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ResultaatType, StatusType, ZaakType
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.api_models.zaken import Resultaat, Status
from zgw_consumers.constants import APITypes

from zac.accounts.tests.factories import (
    BlueprintPermissionFactory,
    SuperUserFactory,
    UserFactory,
)
from zac.core.permissions import zaken_inzien
from zac.core.tests.utils import ClearCachesMixin
from zac.tests import ServiceFactory
from zac.tests.compat import generate_oas_component, mock_service_oas_get
from zac.tests.utils import mock_resource_get, paginated_response
from zgw.models.zrc import Zaak

CATALOGI_ROOT = "http://catalogus.nl/api/v1/"
ZAKEN_ROOT = "http://zaken.nl/api/v1/"
CATALOGUS_URL = f"{CATALOGI_ROOT}catalogussen/e13e72de-56ba-42b6-be36-5c280e9b30cd"


class RelatedCasesResponseTests(APITestCase):
    """
    Test the API response body for zaak-related-cases endpoint.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.user = SuperUserFactory.create()

        ServiceFactory.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        ServiceFactory.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)

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
        )
        related_zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/743b3537-f458-47ef-a1c5-2aa50e4e1563",
            identificatie="ZT2",
            catalogus=CATALOGUS_URL,
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.beperkt_openbaar,
        )
        related_statustype = generate_oas_component(
            "ztc",
            "schemas/StatusType",
            url=f"{CATALOGI_ROOT}statustypen/81cede80-ef69-40e7-b5a1-f5723b586002",
            zaaktype=related_zaaktype["url"],
            volgnummer=1,
        )
        related_resultaattype = generate_oas_component(
            "ztc",
            "schemas/ResultaatType",
            url=f"{CATALOGI_ROOT}resultaattypen/362b23eb-d8a9-486f-b236-8adb58ebc18f",
            zaaktype=related_zaaktype["url"],
            omschrijving="geannuleerd",
        )

        related_zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/3fa0292f-f03a-4b30-8ff5-fad60fdd21a1",
            identificatie="ZAAK-2020-0011",
            bronorganisatie="123456782",
            zaaktype=related_zaaktype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.beperkt_openbaar,
            startdatum="2021-01-01",
            uiterlijkeEinddatumAfdoening="2021-01-21",
            status=f"{ZAKEN_ROOT}statussen/bdab0b31-83b6-452c-9311-9bf40f519de6",
            resultaat=f"{ZAKEN_ROOT}resultaten/c8ebd02f-3265-4f2c-a7d7-f773ad7f589d",
        )
        related_status = generate_oas_component(
            "zrc",
            "schemas/Status",
            url=f"{ZAKEN_ROOT}statussen/bdab0b31-83b6-452c-9311-9bf40f519de6",
            zaak=related_zaak["url"],
            statustype=related_statustype["url"],
            datumStatusGezet="2021-01-01T00:00:00Z",
            statustoelichting="",
        )
        related_resultaat = generate_oas_component(
            "zrc",
            "schemas/Resultaat",
            url=f"{ZAKEN_ROOT}resultaten/c8ebd02f-3265-4f2c-a7d7-f773ad7f589d",
            zaak=related_zaak["url"],
            resultaattype=related_resultaattype["url"],
        )

        cls.zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/e3f5c6d2-0e49-4293-8428-26139f630950",
            identificatie="ZAAK-2020-0010",
            bronorganisatie="123456782",
            zaaktype=cls.zaaktype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
            relevanteAndereZaken=[
                {
                    "aardRelatie": "bijdrage",
                    "url": related_zaak["url"],
                }
            ],
        )

        zaak = factory(Zaak, cls.zaak)
        zaak.zaaktype = factory(ZaakType, cls.zaaktype)

        related_zaak = factory(Zaak, related_zaak)
        related_zaak.zaaktype = factory(ZaakType, related_zaaktype)
        related_zaak.status = factory(Status, related_status)
        related_zaak.status.statustype = factory(StatusType, related_statustype)
        related_zaak.resultaat = factory(Resultaat, related_resultaat)
        related_zaak.resultaat.resultaattype = factory(
            ResultaatType, related_resultaattype
        )

        cls.related_zaak = related_zaak

        cls.find_zaak_patcher = patch("zac.core.api.views.find_zaak", return_value=zaak)
        cls.get_related_zaken_patcher = patch(
            "zac.core.api.views.get_related_zaken",
            return_value=[
                (zaak.relevante_andere_zaken[0]["aard_relatie"], related_zaak)
            ],
        )

        cls.endpoint = reverse(
            "zaak-related",
            kwargs={
                "bronorganisatie": "123456782",
                "identificatie": "ZAAK-2020-0010",
            },
        )

        cls.patch_get_top_level_process_instances = patch(
            "zac.core.api.views.get_top_level_process_instances", return_value=[]
        )

    def setUp(self):
        super().setUp()

        self.find_zaak_patcher.start()
        self.addCleanup(self.find_zaak_patcher.stop)

        self.get_related_zaken_patcher.start()
        self.addCleanup(self.get_related_zaken_patcher.stop)

        # ensure that we have a user with all permissions
        self.client.force_authenticate(user=self.user)

    @freeze_time("2021-01-11T12:00:00Z")
    def test_get_related_cases(self):
        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()

        self.assertEqual(
            response_data,
            [
                {
                    "aardRelatie": "bijdrage",
                    "zaak": {
                        "identificatie": "ZAAK-2020-0011",
                        "bronorganisatie": "123456782",
                        "zaaktype": {
                            "url": f"{CATALOGI_ROOT}zaaktypen/743b3537-f458-47ef-a1c5-2aa50e4e1563",
                            "catalogus": CATALOGUS_URL,
                            "omschrijving": self.related_zaak.zaaktype.omschrijving,
                            "versiedatum": self.related_zaak.zaaktype.versiedatum.isoformat(),
                        },
                        "omschrijving": self.related_zaak.omschrijving,
                        "status": {
                            "url": f"{ZAKEN_ROOT}statussen/bdab0b31-83b6-452c-9311-9bf40f519de6",
                            "datumStatusGezet": "2021-01-01T00:00:00Z",
                            "statustoelichting": "",
                            "statustype": {
                                "url": f"{CATALOGI_ROOT}statustypen/81cede80-ef69-40e7-b5a1-f5723b586002",
                                "omschrijving": self.related_zaak.status.statustype.omschrijving,
                                "omschrijvingGeneriek": self.related_zaak.status.statustype.omschrijving_generiek,
                                "statustekst": self.related_zaak.status.statustype.statustekst,
                                "volgnummer": 1,
                                "isEindstatus": self.related_zaak.status.statustype.is_eindstatus,
                            },
                        },
                        "resultaat": {
                            "url": f"{ZAKEN_ROOT}resultaten/c8ebd02f-3265-4f2c-a7d7-f773ad7f589d",
                            "toelichting": self.related_zaak.resultaat.toelichting,
                            "resultaattype": {
                                "url": f"{CATALOGI_ROOT}resultaattypen/362b23eb-d8a9-486f-b236-8adb58ebc18f",
                                "omschrijving": "geannuleerd",
                            },
                        },
                        "url": self.related_zaak.url,
                    },
                }
            ],
        )

    def test_no_related(self):
        with patch("zac.core.api.views.get_related_zaken", return_value=[]):
            response = self.client.get(self.endpoint)

        self.assertEqual(response.data, [])

    def test_not_found(self):
        with patch("zac.core.api.views.find_zaak", side_effect=ObjectDoesNotExist):
            response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class RelatedCasesPermissionTests(ClearCachesMixin, APITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        ServiceFactory.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        ServiceFactory.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)

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
        cls.get_related_zaken_patcher = patch(
            "zac.core.api.views.get_related_zaken", return_value=[]
        )

        cls.endpoint = reverse(
            "zaak-related",
            kwargs={
                "bronorganisatie": "123456782",
                "identificatie": "ZAAK-2020-0010",
            },
        )

    def setUp(self):
        super().setUp()

        self.find_zaak_patcher.start()
        self.addCleanup(self.find_zaak_patcher.stop)

        self.get_related_zaken_patcher.start()
        self.addCleanup(self.get_related_zaken_patcher.stop)

    def test_not_authenticated(self):
        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_no_permissions(self):
        user = UserFactory.create()
        self.client.force_authenticate(user=user)

        response = self.client.get(self.endpoint)

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

    @requests_mock.Mocker()
    def test_has_perm_but_not_for_va(self, m):
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")

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

    @requests_mock.Mocker()
    def test_has_perm(self, m):
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
