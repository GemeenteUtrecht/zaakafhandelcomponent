from copy import deepcopy
from io import StringIO
from unittest.mock import patch

from django.conf import settings
from django.core.management import call_command

import requests_mock
from rest_framework.test import APITransactionTestCase
from zgw_consumers.constants import APITypes
from zgw_consumers.models import Service

from zac.accounts.datastructures import VA_ORDER
from zac.camunda.constants import AssigneeTypeChoices
from zac.core.tests.utils import ClearCachesMixin
from zac.tests.compat import generate_oas_component, mock_service_oas_get
from zac.tests.utils import mock_resource_get, paginated_response

from ..documents import ZaakDocument
from .utils import ESMixin

CATALOGI_ROOT = "https://api.catalogi.nl/api/v1/"
ZAKEN_ROOT = "https://api.zaken.nl/api/v1/"
CATALOGUS_URL = f"{CATALOGI_ROOT}catalogi/dfb14eb7-9731-4d22-95c2-dff4f33ef36d"


@requests_mock.Mocker()
class IndexZakenTests(ClearCachesMixin, ESMixin, APITransactionTestCase):
    catalogus = generate_oas_component(
        "ztc",
        "schemas/Catalogus",
        url=CATALOGUS_URL,
        domein="DOME",
    )
    zaaktype = generate_oas_component(
        "ztc",
        "schemas/ZaakType",
        url=f"{CATALOGI_ROOT}zaaktypen/a8c8bc90-defa-4548-bacd-793874c013aa",
        catalogus=catalogus["url"],
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

    def setUp(self):
        super().setUp()
        Service.objects.create(api_type=APITypes.ztc, api_root=CATALOGI_ROOT)
        Service.objects.create(api_type=APITypes.zrc, api_root=ZAKEN_ROOT)

    def test_index_zaken_without_rollen(self, m):
        # mock API requests
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")

        m.get(f"{CATALOGI_ROOT}zaaktypen", json=paginated_response([self.zaaktype]))
        m.get(
            f"{ZAKEN_ROOT}zaken",
            json=paginated_response([self.zaak]),
        )
        m.get(
            f"{ZAKEN_ROOT}rollen",
            json=paginated_response([]),
        )
        m.get(
            f"{ZAKEN_ROOT}zaakobjecten?zaak={self.zaak['url']}",
            json=paginated_response([]),
        )
        m.get(f"{ZAKEN_ROOT}zaakinformatieobjecten?zaak={self.zaak['url']}", json=[])
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.catalogus)

        with patch(
            "zac.elasticsearch.management.commands.index_zaken.get_zaakeigenschappen",
            return_value=[],
        ):
            call_command("index_zaken", stdout=StringIO())

        # check zaak_document exists
        zaak_document = ZaakDocument.get(id=self.zaak["url"].split("/")[-1])

        self.assertEqual(zaak_document.identificatie, self.zaak["identificatie"])
        self.assertEqual(zaak_document.bronorganisatie, self.zaak["bronorganisatie"])
        self.assertEqual(zaak_document.zaaktype["url"], self.zaaktype["url"])
        self.assertEqual(
            zaak_document.zaaktype["omschrijving"], self.zaaktype["omschrijving"]
        )
        self.assertEqual(
            zaak_document.zaaktype["catalogus"], self.zaaktype["catalogus"]
        )
        self.assertEqual(
            zaak_document.zaaktype["identificatie"], self.zaaktype["identificatie"]
        )

        self.assertEqual(
            zaak_document.va_order, VA_ORDER[self.zaak["vertrouwelijkheidaanduiding"]]
        )
        self.assertEqual(zaak_document.rollen, [])

    def test_index_zaken_with_rollen(self, m):
        # mock API requests
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")

        # can't use generate_oas_component because of polymorphism
        rol1 = {
            "url": f"{ZAKEN_ROOT}rollen/b80022cf-6084-4cf6-932b-799effdcdb26",
            "zaak": self.zaak["url"],
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
            "zaak": self.zaak["url"],
            "betrokkene": None,
            "betrokkeneType": "medewerker",
            "roltype": f"{CATALOGI_ROOT}roltypen/bfd62804-f46c-42e7-a31c-4139b4c661ac",
            "omschrijving": "zaak behandelaar",
            "omschrijvingGeneriek": "behandelaar",
            "roltoelichting": "some description",
            "registratiedatum": "2020-09-01T00:00:00Z",
            "indicatieMachtiging": "",
            "betrokkeneIdentificatie": {
                "identificatie": f"{AssigneeTypeChoices.user}:some_username",
            },
        }

        m.get(
            f"{CATALOGI_ROOT}zaaktypen",
            json={
                "count": 1,
                "previous": None,
                "next": None,
                "results": [self.zaaktype],
            },
        )
        m.get(
            f"{ZAKEN_ROOT}zaken",
            json=paginated_response([self.zaak]),
        )
        m.get(
            f"{ZAKEN_ROOT}rollen",
            json=paginated_response([rol1, rol2]),
        )
        m.get(
            f"{ZAKEN_ROOT}zaakobjecten?zaak={self.zaak['url']}",
            json=paginated_response([]),
        )
        m.get(f"{ZAKEN_ROOT}zaakinformatieobjecten?zaak={self.zaak['url']}", json=[])
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.catalogus)
        with patch(
            "zac.elasticsearch.management.commands.index_zaken.get_zaakeigenschappen",
            return_value=[],
        ):
            call_command("index_zaken", stdout=StringIO())

        # check zaak_document exists
        zaak_document = ZaakDocument.get(id=self.zaak["url"].split("/")[-1])

        self.assertEqual(zaak_document.identificatie, self.zaak["identificatie"])
        self.assertEqual(zaak_document.bronorganisatie, self.zaak["bronorganisatie"])
        self.assertEqual(zaak_document.zaaktype["url"], self.zaaktype["url"])
        self.assertEqual(
            zaak_document.zaaktype["omschrijving"], self.zaaktype["omschrijving"]
        )
        self.assertEqual(
            zaak_document.zaaktype["catalogus"], self.zaaktype["catalogus"]
        )
        self.assertEqual(
            zaak_document.zaaktype["identificatie"], self.zaaktype["identificatie"]
        )

        self.assertEqual(
            zaak_document.va_order, VA_ORDER[self.zaak["vertrouwelijkheidaanduiding"]]
        )
        self.assertEqual(len(zaak_document.rollen), 2)

        rollen = zaak_document.rollen

        self.assertEqual(rollen[0]["url"], rol1["url"])
        self.assertEqual(rollen[1]["url"], rol2["url"])

    def test_zaken_with_different_rollen(self, m):
        # mock API requests
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")

        # can't use generate_oas_component because of polymorphism
        rol1 = {
            "url": f"{ZAKEN_ROOT}rollen/b80022cf-6084-4cf6-932b-799effdcdb26",
            "zaak": self.zaak["url"],
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
            "zaak": self.zaak["url"],
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
                "results": [self.zaaktype],
            },
        )
        m.get(f"{ZAKEN_ROOT}zaken", json=paginated_response([self.zaak]))
        m.get(f"{ZAKEN_ROOT}rollen", json=paginated_response([rol1, rol2]))
        m.get(
            f"{ZAKEN_ROOT}zaakobjecten?zaak={self.zaak['url']}",
            json=paginated_response([]),
        )
        m.get(f"{ZAKEN_ROOT}zaakinformatieobjecten?zaak={self.zaak['url']}", json=[])
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.catalogus)
        with patch(
            "zac.elasticsearch.management.commands.index_zaken.get_zaakeigenschappen",
            return_value=[],
        ):
            call_command("index_zaken", stdout=StringIO())

        # check zaak_document exists
        zaak_document = ZaakDocument.get(id=self.zaak["url"].split("/")[-1])

        self.assertEqual(zaak_document.identificatie, self.zaak["identificatie"])
        self.assertEqual(zaak_document.bronorganisatie, self.zaak["bronorganisatie"])
        self.assertEqual(zaak_document.zaaktype["url"], self.zaaktype["url"])
        self.assertEqual(
            zaak_document.zaaktype["omschrijving"], self.zaaktype["omschrijving"]
        )
        self.assertEqual(
            zaak_document.zaaktype["catalogus"], self.zaaktype["catalogus"]
        )
        self.assertEqual(
            zaak_document.zaaktype["identificatie"], self.zaaktype["identificatie"]
        )

        self.assertEqual(
            zaak_document.va_order, VA_ORDER[self.zaak["vertrouwelijkheidaanduiding"]]
        )
        self.assertEqual(len(zaak_document.rollen), 2)

        rollen = zaak_document.rollen

        self.assertEqual(rollen[0]["url"], rol1["url"])
        self.assertEqual(rollen[1]["url"], rol2["url"])

    def test_index_zaken_with_eigenschappen(self, m):
        # mock API requests
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")

        eigenschap_tekst = generate_oas_component(
            "ztc",
            "schemas/Eigenschap",
            url=f"{CATALOGI_ROOT}eigenschappen/e3af6a57-4411-4fee-a57f-9f598c3f9d49",
            zaaktype=f"{CATALOGI_ROOT}zaaktypen/a8c8bc90-defa-4548-bacd-793874c013aa",
            specificatie={
                "groep": "dummy",
                "formaat": "tekst",
                "lengte": "3",
                "kardinaliteit": "1",
                "waardenverzameling": [],
            },
        )
        eigenschap_getal = generate_oas_component(
            "ztc",
            "schemas/Eigenschap",
            url=f"{CATALOGI_ROOT}eigenschappen/b7ad0548-8b09-49b2-a559-f430fa9dd0e3",
            zaaktype=f"{CATALOGI_ROOT}zaaktypen/a8c8bc90-defa-4548-bacd-793874c013aa",
            specificatie={
                "groep": "dummy",
                "formaat": "getal",
                "lengte": "2",
                "kardinaliteit": "1",
                "waardenverzameling": [],
            },
        )
        eigenschap_datum = generate_oas_component(
            "ztc",
            "schemas/Eigenschap",
            url=f"{CATALOGI_ROOT}eigenschappen/9e9ee9c0-bf83-4b67-8bfe-90fdd6b3dd94",
            zaaktype=f"{CATALOGI_ROOT}zaaktypen/a8c8bc90-defa-4548-bacd-793874c013aa",
            specificatie={
                "groep": "dummy",
                "formaat": "datum",
                "lengte": "10",
                "kardinaliteit": "1",
                "waardenverzameling": [],
            },
        )
        eigenschap_datum_tijd = generate_oas_component(
            "ztc",
            "schemas/Eigenschap",
            url=f"{CATALOGI_ROOT}eigenschappen/3c008fe4-2aa4-46dc-9bf2-a4590f25c865",
            zaaktype=f"{CATALOGI_ROOT}zaaktypen/a8c8bc90-defa-4548-bacd-793874c013aa",
            specificatie={
                "groep": "dummy",
                "formaat": "datum_tijd",
                "lengte": "25",
                "kardinaliteit": "1",
                "waardenverzameling": [],
            },
        )
        zaak = deepcopy(self.zaak)
        zaak["eigenschappen"] = [
            f"{self.zaak['url']}/eigenschappen/1b2b6aa8-bb41-4168-9c07-f586294f008a",
            f"{self.zaak['url']}/eigenschappen/bbad1fbf-484a-441e-83da-331d3695c45a",
            f"{self.zaak['url']}/eigenschappen/6872ba85-980f-4bcd-be12-1357494a612e",
            f"{self.zaak['url']}/eigenschappen/2449a619-425b-45e5-b4b6-eeb2ba109723",
        ]

        zaak_eigenschap_tekst = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{self.zaak['url']}/eigenschappen/1b2b6aa8-bb41-4168-9c07-f586294f008a",
            zaak=self.zaak["url"],
            eigenschap=eigenschap_tekst["url"],
            naam="textProp",
            waarde="aaa",
        )
        zaak_eigenschap_getal = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{self.zaak['url']}/eigenschappen/bbad1fbf-484a-441e-83da-331d3695c45a",
            zaak=self.zaak["url"],
            eigenschap=eigenschap_getal["url"],
            naam="getalProp",
            waarde="14",
        )
        zaak_eigenschap_datum = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{self.zaak['url']}/eigenschappen/6872ba85-980f-4bcd-be12-1357494a612e",
            zaak=self.zaak["url"],
            eigenschap=eigenschap_datum["url"],
            naam="datumProp",
            waarde="2021-01-02",
        )
        zaak_eigenschap_datum_tijd = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{self.zaak['url']}/eigenschappen/2449a619-425b-45e5-b4b6-eeb2ba109723",
            zaak=self.zaak["url"],
            eigenschap=eigenschap_datum_tijd["url"],
            naam="datumTijdProp",
            waarde="2018-11-13T20:20:39+00:00",
        )
        m.get(f"{CATALOGI_ROOT}zaaktypen", json=paginated_response([self.zaaktype]))
        m.get(
            f"{CATALOGI_ROOT}eigenschappen?zaaktype={self.zaaktype['url']}",
            json=paginated_response(
                [
                    eigenschap_tekst,
                    eigenschap_getal,
                    eigenschap_datum,
                    eigenschap_datum_tijd,
                ]
            ),
        )

        m.get(f"{ZAKEN_ROOT}zaken", json=paginated_response([zaak]))
        m.get(f"{ZAKEN_ROOT}rollen", json=paginated_response([]))
        m.get(
            f"{self.zaak['url']}/zaakeigenschappen",
            json=[
                zaak_eigenschap_tekst,
                zaak_eigenschap_getal,
                zaak_eigenschap_datum,
                zaak_eigenschap_datum_tijd,
            ],
        )
        m.get(
            f"{ZAKEN_ROOT}zaakobjecten?zaak={zaak['url']}", json=paginated_response([])
        )
        m.get(f"{ZAKEN_ROOT}zaakinformatieobjecten?zaak={zaak['url']}", json=[])
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.catalogus)
        call_command("index_zaken", stdout=StringIO())

        # check zaak_document exists
        zaak_id = self.zaak["url"].split("/")[-1]
        zaak_document = ZaakDocument.get(id=zaak_id)

        self.assertEqual(zaak_document.identificatie, self.zaak["identificatie"])
        self.assertEqual(zaak_document.bronorganisatie, self.zaak["bronorganisatie"])
        self.assertEqual(zaak_document.zaaktype["url"], self.zaaktype["url"])
        self.assertEqual(
            zaak_document.zaaktype["omschrijving"], self.zaaktype["omschrijving"]
        )
        self.assertEqual(
            zaak_document.zaaktype["catalogus"], self.zaaktype["catalogus"]
        )
        self.assertEqual(
            zaak_document.zaaktype["identificatie"], self.zaaktype["identificatie"]
        )

        # check zaak eigenschappen
        zaak_eigenschappen = zaak_document.eigenschappen
        self.assertEqual(
            zaak_eigenschappen,
            {
                "tekst": {"textProp": "aaa"},
                "getal": {"getalProp": "14"},
                "datum": {"datumProp": "2021-01-02"},
                "datum_tijd": {"datumTijdProp": "2018-11-13T20:20:39+00:00"},
            },
        )

        # check zaak eigenschap mappings
        self.refresh_index()
        index = zaak_document._index
        eigenschap_mappings = index.get_field_mapping(fields="eigenschappen.*")[
            settings.ES_INDEX_ZAKEN
        ]["mappings"]

        self.assertEqual(len(eigenschap_mappings.keys()), 4)
        self.assertEqual(
            eigenschap_mappings["eigenschappen.tekst.textProp"]["mapping"]["textProp"][
                "type"
            ],
            "keyword",
        )
        self.assertEqual(
            eigenschap_mappings["eigenschappen.getal.getalProp"]["mapping"][
                "getalProp"
            ]["type"],
            "integer",
        )
        self.assertEqual(
            eigenschap_mappings["eigenschappen.datum.datumProp"]["mapping"][
                "datumProp"
            ]["type"],
            "date",
        )
        self.assertEqual(
            eigenschap_mappings["eigenschappen.datum_tijd.datumTijdProp"]["mapping"][
                "datumTijdProp"
            ]["type"],
            "date",
        )

    def test_index_zaken_with_eigenschap_with_point(self, m):
        # mock API requests
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")

        eigenschap_tekst = generate_oas_component(
            "ztc",
            "schemas/Eigenschap",
            url=f"{CATALOGI_ROOT}eigenschappen/e3af6a57-4411-4fee-a57f-9f598c3f9d49",
            zaaktype=f"{CATALOGI_ROOT}zaaktypen/a8c8bc90-defa-4548-bacd-793874c013aa",
            specificatie={
                "groep": "dummy",
                "formaat": "tekst",
                "lengte": "3",
                "kardinaliteit": "1",
                "waardenverzameling": [],
            },
        )
        zaak = deepcopy(self.zaak)
        zaak["eigenschappen"] = [
            f"{zaak['url']}/eigenschappen/1b2b6aa8-bb41-4168-9c07-f586294f008a"
        ]

        zaak_eigenschap_tekst = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{zaak['url']}/eigenschappen/1b2b6aa8-bb41-4168-9c07-f586294f008a",
            zaak=zaak["url"],
            eigenschap=eigenschap_tekst["url"],
            naam="Bedrag incl. BTW",
            waarde="aaa",
        )
        m.get(f"{CATALOGI_ROOT}zaaktypen", json=paginated_response([self.zaaktype]))
        m.get(
            f"{CATALOGI_ROOT}eigenschappen?zaaktype={self.zaaktype['url']}",
            json=paginated_response([eigenschap_tekst]),
        )

        m.get(f"{ZAKEN_ROOT}zaken", json=paginated_response([zaak]))
        m.get(f"{ZAKEN_ROOT}rollen", json=paginated_response([]))
        m.get(f"{zaak['url']}/zaakeigenschappen", json=[zaak_eigenschap_tekst])
        m.get(
            f"{ZAKEN_ROOT}zaakobjecten?zaak={zaak['url']}", json=paginated_response([])
        )

        m.get(f"{ZAKEN_ROOT}zaakinformatieobjecten?zaak={zaak['url']}", json=[])
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.catalogus)
        call_command("index_zaken", stdout=StringIO())

        # check zaak_document exists
        zaak_id = zaak["url"].split("/")[-1]
        zaak_document = ZaakDocument.get(id=zaak_id)

        self.assertEqual(zaak_document.identificatie, zaak["identificatie"])
        self.assertEqual(zaak_document.bronorganisatie, zaak["bronorganisatie"])
        self.assertEqual(zaak_document.zaaktype["url"], self.zaaktype["url"])
        self.assertEqual(
            zaak_document.zaaktype["omschrijving"], self.zaaktype["omschrijving"]
        )
        self.assertEqual(
            zaak_document.zaaktype["catalogus"], self.zaaktype["catalogus"]
        )
        self.assertEqual(
            zaak_document.zaaktype["identificatie"], self.zaaktype["identificatie"]
        )

        # check zaak eigenschappen
        zaak_eigenschappen = zaak_document.eigenschappen
        self.assertEqual(zaak_eigenschappen, {"tekst": {"Bedrag incl  BTW": "aaa"}})

        # check zaak eigenschap mappings
        self.refresh_index()
        index = zaak_document._index
        eigenschap_mappings = index.get_field_mapping(fields="eigenschappen.*")[
            settings.ES_INDEX_ZAKEN
        ]["mappings"]

        self.assertEqual(len(eigenschap_mappings.keys()), 1)
        self.assertEqual(
            eigenschap_mappings["eigenschappen.tekst.Bedrag incl  BTW"]["mapping"][
                "Bedrag incl  BTW"
            ]["type"],
            "keyword",
        )

    def test_index_zaken_with_status(self, m):
        # mock API requests
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")
        zaak = deepcopy(self.zaak)
        zaak["status"] = f"{ZAKEN_ROOT}statussen/dd4573d0-4d99-4e90-a05c-e08911e8673e"

        status_response = generate_oas_component(
            "zrc",
            "schemas/Status",
            url=f"{ZAKEN_ROOT}statussen/dd4573d0-4d99-4e90-a05c-e08911e8673e",
            statustype=f"{CATALOGI_ROOT}statustypen/c612f300-8e16-4811-84f4-78c99fdebe74",
            statustoelichting="some-statustoelichting",
            zaak=zaak["url"],
        )
        statustype_response = generate_oas_component(
            "ztc",
            "schemas/StatusType",
            url=f"{CATALOGI_ROOT}statustypen/c612f300-8e16-4811-84f4-78c99fdebe74",
        )
        m.get(
            f"{CATALOGI_ROOT}zaaktypen",
            json={
                "count": 1,
                "previous": None,
                "next": None,
                "results": [self.zaaktype],
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
        m.get(
            f"{ZAKEN_ROOT}zaakobjecten?zaak={zaak['url']}", json=paginated_response([])
        )
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.catalogus)
        m.get(
            f"{ZAKEN_ROOT}statussen/dd4573d0-4d99-4e90-a05c-e08911e8673e",
            json=status_response,
        )
        m.get(
            f"{CATALOGI_ROOT}statustypen/c612f300-8e16-4811-84f4-78c99fdebe74",
            json=statustype_response,
        )

        m.get(f"{ZAKEN_ROOT}zaakinformatieobjecten?zaak={zaak['url']}", json=[])
        with patch(
            "zac.elasticsearch.management.commands.index_zaken.get_zaakeigenschappen",
            return_value=[],
        ):
            call_command("index_zaken", stdout=StringIO())

        # check zaak_document exists
        zaak_document = ZaakDocument.get(id=zaak["url"].split("/")[-1])
        self.assertEqual(
            zaak_document.status.statustoelichting, "some-statustoelichting"
        )

    def test_index_zaken_reindex_last_argument(self, m):
        # mock API requests
        mock_service_oas_get(m, CATALOGI_ROOT, "ztc")
        mock_service_oas_get(m, ZAKEN_ROOT, "zrc")

        m.get(
            f"{CATALOGI_ROOT}zaaktypen",
            json={
                "count": 1,
                "previous": None,
                "next": None,
                "results": [self.zaaktype],
            },
        )
        m.get(f"{ZAKEN_ROOT}zaken", json=paginated_response([self.zaak]))
        m.get(f"{ZAKEN_ROOT}rollen", json=paginated_response([]))
        m.get(
            f"{ZAKEN_ROOT}zaakobjecten?zaak={self.zaak['url']}",
            json=paginated_response([]),
        )

        m.get(f"{ZAKEN_ROOT}zaakinformatieobjecten?zaak={self.zaak['url']}", json=[])
        mock_resource_get(m, self.zaaktype)
        mock_resource_get(m, self.catalogus)
        with patch(
            "zac.elasticsearch.management.commands.index_zaken.get_zaakeigenschappen",
            return_value=[],
        ):
            call_command("index_zaken")
        zd = ZaakDocument.get(id=self.zaak["url"].split("/")[-1])
        self.assertEqual(zd.identificatie, self.zaak["identificatie"])
        zaak2 = generate_oas_component(
            "zrc",
            "schemas/Zaak",
            url=f"{ZAKEN_ROOT}zaken/a522d30c-6c10-47fe-82e3-e9f524c14ca9",
            zaaktype=self.zaaktype["url"],
            bronorganisatie="002220647",
            identificatie="ZAAK-002",
            vertrouwelijkheidaanduiding="zaakvertrouwelijk",
            status=None,
        )
        m.get(f"{ZAKEN_ROOT}zaken", json=paginated_response([zaak2, self.zaak]))
        m.get(
            f"{ZAKEN_ROOT}zaakobjecten?zaak={zaak2['url']}", json=paginated_response([])
        )
        m.get(f"{ZAKEN_ROOT}zaakinformatieobjecten?zaak={zaak2['url']}", json=[])
        with patch(
            "zac.elasticsearch.management.commands.index_zaken.get_zaakeigenschappen",
            return_value=[],
        ):
            call_command("index_zaken", reindex_last=1)

        # check zaak_document exists
        zaak2_id = zaak2["url"].split("/")[-1]
        zd2 = ZaakDocument.get(id=zaak2_id)
        self.assertEqual(zd2.identificatie, "ZAAK-002")
