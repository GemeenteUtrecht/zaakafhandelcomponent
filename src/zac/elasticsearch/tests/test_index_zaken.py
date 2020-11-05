from django.core.management import call_command
from django.test import TestCase

import requests_mock
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from zac.core.tests.utils import ClearCachesMixin
from zac.tests.utils import generate_oas_component, mock_service_oas_get

from ..documents import ZaakDocument
from .utils import ESMixin

CATALOGI_ROOT = "https://api.catalogi.nl/api/v1/"
ZAKEN_ROOT = "https://api.zaken.nl/api/v1/"


@requests_mock.Mocker()
class IndexZakenTests(ClearCachesMixin, ESMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)

    def test_index_zaken_without_rollen(self, m):
        # mock API requests
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/a8c8bc90-defa-4548-bacd-793874c013aa",
        )
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
            zaaktype=zaaktype["url"],
            bronorganisatie="002220647",
            identificatie="ZAAK1",
            vertrouwelijkheidaanduiding="zaakvertrouwelijk",
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
        m.get(
            f"{ZAKEN_ROOT}zaken",
            json={"count": 1, "previous": None, "next": None, "results": [zaak]},
        )
        m.get(
            f"{ZAKEN_ROOT}rollen",
            json={"count": 0, "previous": None, "next": None, "results": []},
        )

        call_command("index_zaken")

        # check zaak_document exists
        zaak_document = ZaakDocument.get(id="a522d30c-6c10-47fe-82e3-e9f524c14ca8")

        self.assertEqual(zaak_document.identificatie, "ZAAK1")
        self.assertEqual(zaak_document.bronorganisatie, "002220647")
        self.assertEqual(zaak_document.zaaktype, zaaktype["url"])
        self.assertEqual(zaak_document.va_order, 18)
        self.assertEqual(zaak_document.rollen, [])

    def test_index_zaken_with_rollen(self, m):
        # mock API requests
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/a8c8bc90-defa-4548-bacd-793874c013aa",
        )
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/69e98129-1f0d-497f-bbfb-84b88137edbc",
            zaaktype=zaaktype["url"],
            bronorganisatie="002220647",
            identificatie="ZAAK1",
            vertrouwelijkheidaanduiding="zaakvertrouwelijk",
        )
        # can't use generate_oas_component because of polymorphism
        rol1 = {
            "url": f"{ZAKEN_ROOT}rollen/b80022cf-6084-4cf6-932b-799effdcdb26",
            "zaak": zaak["url"],
            "betrokkene": None,
            "betrokkeneType": "organisatorische_eenheid",
            "roltype": f"{CATALOGI_ROOT}roltypen/bfd62804-f46c-42e7-a31c-4139b4c661ac",
            "omschrijving": "zaak behandelaar",
            "omschrijvingGeneriek": "behandelaar",
            "roltoelichting": "some description",
            "registratiedatum": "2020-09-01T00:00:00Z",
            "indicatieMachtiging": "",
            "betrokkeneIdentificatie": {
                "identificatie": "123456",
            },
        }
        rol2 = {
            "url": f"{ZAKEN_ROOT}rollen/de7039d7-242a-4186-91c3-c3b49228211a",
            "zaak": zaak["url"],
            "betrokkene": None,
            "betrokkeneType": "medewerker",
            "roltype": f"{CATALOGI_ROOT}roltypen/bfd62804-f46c-42e7-a31c-4139b4c661ac",
            "omschrijving": "zaak behandelaar",
            "omschrijvingGeneriek": "behandelaar",
            "roltoelichting": "some description",
            "registratiedatum": "2020-09-01T00:00:00Z",
            "indicatieMachtiging": "",
            "betrokkeneIdentificatie": {
                "identificatie": "some_username",
            },
        }

        m.get(
            f"{CATALOGI_ROOT}zaaktypen",
            json={
                "count": 1,
                "previous": None,
                "next": None,
                "results": [zaaktype],
            },
        )
        m.get(
            f"{ZAKEN_ROOT}zaken",
            json={"count": 1, "previous": None, "next": None, "results": [zaak]},
        )
        m.get(
            f"{ZAKEN_ROOT}rollen",
            json={"count": 1, "previous": None, "next": None, "results": [rol1, rol2]},
        )

        call_command("index_zaken")

        # check zaak_document exists
        zaak_document = ZaakDocument.get(id="69e98129-1f0d-497f-bbfb-84b88137edbc")

        self.assertEqual(zaak_document.identificatie, "ZAAK1")
        self.assertEqual(zaak_document.bronorganisatie, "002220647")
        self.assertEqual(zaak_document.zaaktype, zaaktype["url"])
        self.assertEqual(zaak_document.va_order, 18)
        self.assertEqual(len(zaak_document.rollen), 2)

        rollen = zaak_document.rollen

        self.assertEqual(rollen[0]["url"], rol1["url"])
        self.assertEqual(rollen[1]["url"], rol2["url"])

    def test_zaken_with_different_rollen(self, m):
        # mock API requests
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        zaaktype = generate_oas_component(
            "ztc",
            "schemas/ZaakType",
            url=f"{CATALOGI_ROOT}zaaktypen/a8c8bc90-defa-4548-bacd-793874c013aa",
        )
        zaak = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/69e98129-1f0d-497f-bbfb-84b88137edbc",
            zaaktype=zaaktype["url"],
            bronorganisatie="002220647",
            identificatie="ZAAK1",
            vertrouwelijkheidaanduiding="zaakvertrouwelijk",
        )
        # can't use generate_oas_component because of polymorphism
        rol1 = {
            "url": f"{ZAKEN_ROOT}rollen/b80022cf-6084-4cf6-932b-799effdcdb26",
            "zaak": zaak["url"],
            "betrokkene": None,
            "betrokkeneType": "natuurlijk_persoon",
            "roltype": f"{CATALOGI_ROOT}roltypen/bfd62804-f46c-42e7-a31c-4139b4c661ac",
            "omschrijving": "zaak behandelaar",
            "omschrijvingGeneriek": "behandelaar",
            "roltoelichting": "some description",
            "registratiedatum": "2020-09-01T00:00:00Z",
            "indicatieMachtiging": "",
            "betrokkeneIdentificatie": {
                "geboortedatum": "2020-01-01",
            },
        }
        rol2 = {
            "url": f"{ZAKEN_ROOT}rollen/de7039d7-242a-4186-91c3-c3b49228211a",
            "zaak": zaak["url"],
            "betrokkene": None,
            "betrokkeneType": "natuurlijk_persoon",
            "roltype": f"{CATALOGI_ROOT}roltypen/bfd62804-f46c-42e7-a31c-4139b4c661ac",
            "omschrijving": "zaak behandelaar",
            "omschrijvingGeneriek": "behandelaar",
            "roltoelichting": "other description",
            "registratiedatum": "2020-09-01T00:00:00Z",
            "indicatieMachtiging": "",
            "betrokkeneIdentificatie": {
                "geboortedatum": "",
            },
        }

        m.get(
            f"{CATALOGI_ROOT}zaaktypen",
            json={
                "count": 1,
                "previous": None,
                "next": None,
                "results": [zaaktype],
            },
        )
        m.get(
            f"{ZAKEN_ROOT}zaken",
            json={"count": 1, "previous": None, "next": None, "results": [zaak]},
        )
        m.get(
            f"{ZAKEN_ROOT}rollen",
            json={"count": 1, "previous": None, "next": None, "results": [rol1, rol2]},
        )

        call_command("index_zaken")

        # check zaak_document exists
        zaak_document = ZaakDocument.get(id="69e98129-1f0d-497f-bbfb-84b88137edbc")

        self.assertEqual(zaak_document.identificatie, "ZAAK1")
        self.assertEqual(zaak_document.bronorganisatie, "002220647")
        self.assertEqual(zaak_document.zaaktype, zaaktype["url"])
        self.assertEqual(zaak_document.va_order, 18)
        self.assertEqual(len(zaak_document.rollen), 2)

        rollen = zaak_document.rollen

        self.assertEqual(rollen[0]["url"], rol1["url"])
        self.assertEqual(rollen[1]["url"], rol2["url"])
