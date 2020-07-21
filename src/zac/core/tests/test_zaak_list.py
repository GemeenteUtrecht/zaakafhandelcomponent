from urllib.parse import parse_qs, urlsplit

from django.conf import settings
from django.urls import reverse_lazy

import requests_mock
from django_webtest import TransactionWebTest
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from zac.accounts.tests.factories import PermissionSetFactory, UserFactory
from zac.tests.utils import generate_oas_component, mock_service_oas_get

from ..permissions import zaken_inzien
from .utils import ClearCachesMixin

CATALOGI_ROOT = "https://api.catalogi.nl/api/v1/"
ZAKEN_ROOT = "https://api.zaken.nl/api/v1/"


@requests_mock.Mocker()
class ZaakListTests(ClearCachesMixin, TransactionWebTest):

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
            json={"count": 1, "previous": None, "next": None, "results": [zaaktype],},
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
            response.context["filter_form"].fields["zaaktypen"].choices, [],
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
        )
        zt2 = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            catalogus=catalogus,
            url=f"{CATALOGI_ROOT}zaaktypen/ce05e9c7-b9cd-42d1-ba0e-e0b3d2001be9",
            identificatie="ZT2",
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktypen",
            json={"count": 2, "previous": None, "next": None, "results": [zt1, zt2],},
        )
        # set up user permissions
        PermissionSetFactory.create(
            permissions=[zaken_inzien.name],
            for_user=self.user,
            catalogus=catalogus,
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.zeer_geheim,
        )
        # set up zaken API data
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
            zaaktype=zt1["url"],
            vertrouwelijkheidaanduiding=zt1["vertrouwelijkheidaanduiding"],
        )
        m.get(
            f"{ZAKEN_ROOT}zaken",
            json={"count": 1, "previous": None, "next": None, "results": [zaak]},
        )

        response = self.app.get(self.url, user=self.user)

        self.assertEqual(response.status_code, 200)

        zt_choices = response.context["filter_form"].fields["zaaktypen"].choices
        self.assertEqual(len(zt_choices), 1)
        self.assertEqual(zt_choices[0][0], zt1["url"])

        zaken = response.context["zaken"]
        self.assertEqual(len(zaken), 1)
        self.assertEqual(zaken[0].url, zaak["url"])

        # verify API calls
        self.assertEqual(
            len(m.request_history), 5,
        )
        (
            req_ztc_schema,
            req_zaaktypen,
            req_zaaktypen_catalogus,
            req_zrc_schema,
            req_zaken,
        ) = m.request_history
        query = parse_qs(req_zaken.query)

        self.assertEqual(len(query["zaaktype"]), 1)
        self.assertEqual(query["zaaktype"][0], zt1["url"])

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
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktypen",
            json={"count": 1, "previous": None, "next": None, "results": [zaaktype],},
        )
        # set up user permissions
        PermissionSetFactory.create(
            permissions=[zaken_inzien.name],
            for_user=self.user,
            catalogus=catalogus,
            zaaktype_identificaties=["ZT1"],
            max_va=VertrouwelijkheidsAanduidingen.openbaar,
        )
        # set up zaken API data
        zaak1 = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
            zaaktype=zaaktype["url"],
            vertrouwelijkheidaanduiding=VertrouwelijkheidsAanduidingen.openbaar,
        )
        m.get(
            f"{ZAKEN_ROOT}zaken?maximaleVertrouwelijkheidaanduiding=openbaar",
            json={"count": 2, "previous": None, "next": None, "results": [zaak1],},
        )

        response = self.app.get(self.url, user=self.user)

        # note that requests_mock defaults to case-insensitive
        self.assertEqual(
            m.last_request.qs["maximalevertrouwelijkheidaanduiding"],
            [VertrouwelijkheidsAanduidingen.openbaar],
        )

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
            json={"count": 2, "previous": None, "next": None, "results": [zt1, zt2],},
        )
        m.get(
            f"{ZAKEN_ROOT}zaken?zaaktype={zt1['url']}",
            json={"count": 2, "previous": None, "next": None, "results": [zaak1],},
        )

        response = self.app.get(self.url, {"zaaktypen": zt1["url"]}, user=superuser)

        self.assertEqual(response.status_code, 200)

        zaken = response.context["zaken"]
        self.assertEqual(len(zaken), 1)
        self.assertEqual(zaken[0].url, zaak1["url"])

        # verify API calls
        req_zaken = m.last_request
        query = parse_qs(req_zaken.query)
        self.assertEqual(len(query["zaaktype"]), 1)
        self.assertEqual(query["zaaktype"][0], zt1["url"])
