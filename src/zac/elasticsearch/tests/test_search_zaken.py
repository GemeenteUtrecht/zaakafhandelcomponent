from django.conf import settings
from django.test import TestCase

from elasticsearch_dsl import Index
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen

from ..documents import ZaakDocument
from ..searches import search
from .utils import ESMixin

CATALOGI_ROOT = "https://api.catalogi.nl/api/v1/"
ZAKEN_ROOT = "https://api.zaken.nl/api/v1/"


class SearchZakenTests(ESMixin, TestCase):
    def setUp(self) -> None:
        super().setUp()

        self.zaak_document1 = ZaakDocument(
            meta={"id": "a522d30c-6c10-47fe-82e3-e9f524c14ca8"},
            url=f"{ZAKEN_ROOT}zaken/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
            zaaktype=f"{CATALOGI_ROOT}zaaktypen/a8c8bc90-defa-4548-bacd-793874c013aa",
            identificatie="ZAAK1",
            bronorganisatie="123456",
            vertrouwelijkheidaanduiding="beperkt_openbaar",
            va_order=16,
            rollen=[
                {
                    "url": f"{ZAKEN_ROOT}rollen/b80022cf-6084-4cf6-932b-799effdcdb26",
                    "betrokkene_type": "organisatorische_eenheid",
                    "betrokkene_identificatie": {
                        "identificatie": "123456",
                    },
                },
                {
                    "url": f"{ZAKEN_ROOT}rollen/de7039d7-242a-4186-91c3-c3b49228211a",
                    "betrokkene_type": "medewerker",
                    "omschrijving_generiek": "behandelaar",
                    "betrokkene_identificatie": {
                        "identificatie": "some_username",
                    },
                },
            ],
        )
        self.zaak_document1.save()

        self.zaak_document2 = ZaakDocument(
            meta={"id": "a8c8bc90-defa-4548-bacd-793874c013aa"},
            url="https://api.zaken.nl/api/v1/zaken/a8c8bc90-defa-4548-bacd-793874c013aa",
            zaaktype="https://api.catalogi.nl/api/v1/zaaktypen/de7039d7-242a-4186-91c3-c3b49228211a",
            identificatie="ZAAK2",
            bronorganisatie="7890",
            vertrouwelijkheidaanduiding="confidentieel",
            va_order=20,
            rollen=[],
        )
        self.zaak_document2.save()

        zaken = Index(settings.ES_INDEX_ZAKEN)
        zaken.refresh()

    def test_search_zaaktype(self):
        result = search(
            zaaktypen=[
                "https://api.catalogi.nl/api/v1/zaaktypen/a8c8bc90-defa-4548-bacd-793874c013aa"
            ]
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], self.zaak_document1.url)

    def test_search_identificatie(self):
        result = search(identificatie="ZAAK1")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], self.zaak_document1.url)

    def test_search_bronorg(self):
        result = search(bronorganisatie="123456")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], self.zaak_document1.url)

    def test_search_behandelaar(self):
        result = search(behandelaar="some_username")

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], self.zaak_document1.url)

    def test_search_allowed(self):
        allowed = [
            {
                "zaaktypen": [
                    "https://api.catalogi.nl/api/v1/zaaktypen/a8c8bc90-defa-4548-bacd-793874c013aa"
                ],
                "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
                "oo": "123456",
            }
        ]

        result = search(allowed=allowed)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], self.zaak_document1.url)

    def test_combined(self):
        result = search(
            zaaktypen=[
                "https://api.catalogi.nl/api/v1/zaaktypen/a8c8bc90-defa-4548-bacd-793874c013aa"
            ],
            bronorganisatie="123456",
            identificatie="ZAAK1",
            allowed=[
                {
                    "zaaktypen": [
                        "https://api.catalogi.nl/api/v1/zaaktypen/a8c8bc90-defa-4548-bacd-793874c013aa"
                    ],
                    "max_va": VertrouwelijkheidsAanduidingen.zaakvertrouwelijk,
                    "oo": "123456",
                }
            ],
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], self.zaak_document1.url)
