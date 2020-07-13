from django.test import TestCase
from django.urls import reverse_lazy

import requests_mock
from django_webtest import WebTest
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from zac.accounts.tests.factories import UserFactory
from zac.contrib.brp.models import BRPConfig
from zac.tests.utils import (
    generate_oas_component,
    mock_service_oas_get,
    paginated_response,
)

from .utils import ClearCachesMixin

CATALOGI_ROOT = "https://api.catalogi.nl/api/v1/"
ZAKEN_ROOT = "https://api.zaken.nl/api/v1/"

PAND1 = "https://api.bag.nl/api/v1/panden/12345"
PAND2 = "https://api.bag.nl/api/v1/panden/67890"

BRP_API_ROOT = "https://api.brp.nl/api/v1/"
BSN1 = "1234567"
BSN2 = "890"


class SearchWebTest(ClearCachesMixin, WebTest):
    url = reverse_lazy("core:search-index")

    def setUp(self) -> None:
        self.user = UserFactory.create()
        self.app.set_user(self.user)

    def test_display_brp(self):
        response = self.app.get(self.url)

        # there is bsn radio button
        bsn_radio = response.html.find(id="object-types-brp").find(
            "input", type="radio"
        )
        self.assertIsNotNone(bsn_radio)
        self.assertEqual(bsn_radio.attrs["value"], "bsn")

        # there is bsn input field
        bsn_input = response.html.find(id="object-types-brp-bsn").find(
            "input", type="text"
        )
        self.assertIsNotNone(bsn_input)
        self.assertEqual(bsn_input.attrs["name"], "bsn")


@requests_mock.Mocker()
class SearchResultWebTest(ClearCachesMixin, TestCase):
    url = reverse_lazy("core:search-results")

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory.create()

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)
        brp = Service.objects.create(api_type=APITypes.orc, api_root=BRP_API_ROOT)

        brp_config = BRPConfig.get_solo()
        brp_config.service = brp
        brp_config.save()

    def setUp(self) -> None:
        super().setUp()
        self.client.force_login(self.user)

    def _setUpMocks(self, m):
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/17e08a91-67ff-401d-aae1-69b1beeeff06",
            catalogus=f"{CATALOGI_ROOT}catalogi/dfb14eb7-9731-4d22-95c2-dff4f33ef36d",
        )
        zaak1 = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/05b2c190-b1f6-4767-9e35-38bcf7702968",
            zaaktype=zaaktype["url"],
            identificatie="zaak1",
        )
        zaak2 = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/ee512886-d0d9-4c12-9bbb-78b0d22bfb61",
            zaaktype=zaaktype["url"],
            identificatie="zaak2",
        )
        zaak3 = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/52ed815d-7b3e-45a9-bf47-233baec2198f",
            zaaktype=zaaktype["url"],
            identificatie="zaak3",
        )
        # generate_oas_component doesn't support polymorphic objects
        zaakobject1 = {
            "url": f"{ZAKEN_ROOT}zaakobjecten/ee512886-d0d9-4c12-9bbb-78b0d22bfb61",
            "zaak": zaak1["url"],
            "object": PAND1,
        }
        zaakobject2 = {
            "url": f"{ZAKEN_ROOT}zaakobjecten/05b2c190-b1f6-4767-9e35-38bcf7702968",
            "zaak": zaak2["url"],
            "object": PAND2,
        }
        rol1 = {
            "url": f"{ZAKEN_ROOT}rollen/ee512886-d0d9-4c12-9bbb-78b0d22bfb61",
            "zaak": zaak1["url"],
            "betrokkene": "",
        }
        rol2 = {
            "url": f"{ZAKEN_ROOT}rollen/05b2c190-b1f6-4767-9e35-38bcf7702968",
            "zaak": zaak1["url"],
            "betrokkene": "",
        }
        rol3 = {
            "url": f"{ZAKEN_ROOT}rollen/52ed815d-7b3e-45a9-bf47-233baec2198f",
            "zaak": zaak2["url"],
            "betrokkene": None,
            "betrokkeneIdentificatie": {"inpBsn": BSN1,},
        }
        rol4 = {
            "url": f"{ZAKEN_ROOT}rollen/2d04238d-2b74-41bd-a556-2a15e646ef6b",
            "zaak": zaak3["url"],
            "betrokkene": None,
            "betrokkeneIdentificatie": {"inpBsn": BSN2,},
        }

        m.get(
            f"{ZAKEN_ROOT}zaakobjecten?object={PAND1}",
            json=paginated_response([zaakobject1]),
        )
        m.get(
            f"{ZAKEN_ROOT}rollen?betrokkene={BRP_API_ROOT}ingeschrevenpersonen/{BSN1}",
            json=paginated_response([rol1]),
        )
        m.get(
            f"{ZAKEN_ROOT}rollen?betrokkene={BRP_API_ROOT}ingeschrevenpersonen?burgerservicenummer={BSN1}",
            json=paginated_response([rol2]),
        )
        m.get(
            f"{ZAKEN_ROOT}rollen?betrokkeneIdentificatie__natuurlijkPersoon__inpBsn={BSN1}",
            json=paginated_response([rol3]),
        )
        m.get(zaak1["url"], json=zaak1)
        m.get(zaak2["url"], json=zaak2)
        m.get(zaak3["url"], json=zaak3)
        m.get(zaaktype["url"], json=zaaktype)

    def test_search_bag(self, m):
        self._setUpMocks(m)
        data = {
            "registration": "bag",
            "object_type": "pand",
            "pand": f"{PAND1}?geldigOp=2020-01-01",
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 200)

        zaken = response.context_data["zaken"]
        self.assertEqual(len(zaken), 1)

        zaak = zaken[0]
        self.assertEqual(zaak.identificatie, "zaak1")

    def test_search_brp(self, m):
        self._setUpMocks(m)
        data = {
            "registration": "brp",
            "object_type": "bsn",
            "bsn": BSN1,
        }

        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 200)

        zaken = response.context_data["zaken"]
        self.assertEqual(len(zaken), 2)

        zaak1, zaak2 = sorted(zaken, key=lambda x: x.identificatie)
        self.assertEqual(zaak1.identificatie, "zaak1")
        self.assertEqual(zaak2.identificatie, "zaak2")
