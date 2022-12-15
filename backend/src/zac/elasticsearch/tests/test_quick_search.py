import json

from django.conf import settings
from django.test import TestCase

from elasticsearch_dsl import Index

from zac.camunda.constants import AssigneeTypeChoices

from ..documents import (
    InformatieObjectDocument,
    ObjectDocument,
    ObjectRecordDocument,
    ZaakDocument,
    ZaakTypeDocument,
    edge_ngram_analyzer,
)
from ..searches import quick_search
from .utils import ESMixin

CATALOGI_ROOT = "https://api.catalogi.nl/api/v1/"
ZAKEN_ROOT = "https://api.zaken.nl/api/v1/"


class QuickSearchTests(ESMixin, TestCase):
    @staticmethod
    def clear_index(init=False):
        ESMixin.clear_index(init=init)
        Index(settings.ES_INDEX_OBJECTEN).delete(ignore=404)
        Index(settings.ES_INDEX_DOCUMENTEN).delete(ignore=404)

        if init:
            ObjectDocument.init()
            InformatieObjectDocument.init()

    @staticmethod
    def refresh_index():
        ESMixin.refresh_index()
        Index(settings.ES_INDEX_OBJECTEN).refresh()
        Index(settings.ES_INDEX_DOCUMENTEN).refresh()

    def setUp(self) -> None:
        super().setUp()
        self.zaaktype_document1 = ZaakTypeDocument(
            url=f"{CATALOGI_ROOT}zaaktypen/a8c8bc90-defa-4548-bacd-793874c013aa",
            catalogus=f"{CATALOGI_ROOT}catalogussen/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
            omschrijving="zaaktype1",
        )
        self.zaak_document1 = ZaakDocument(
            meta={"id": "a522d30c-6c10-47fe-82e3-e9f524c14ca8"},
            url=f"{ZAKEN_ROOT}zaken/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
            zaaktype=self.zaaktype_document1,
            identificatie="ZAAK-2022-0000001010",
            bronorganisatie="123456",
            omschrijving="Some zaak description",
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
                        "identificatie": f"{AssigneeTypeChoices.user}:some_username",
                    },
                },
            ],
            eigenschappen={
                "tekst": {
                    "Beleidsveld": "Asiel en Integratie",
                    "Bedrag incl  BTW": "aaa",
                }
            },
            deadline="2021-12-31",
        )
        self.zaak_document1.save()
        self.zaaktype_document2 = ZaakTypeDocument(
            url=f"{CATALOGI_ROOT}zaaktypen/de7039d7-242a-4186-91c3-c3b49228211a",
            catalogus=f"{CATALOGI_ROOT}catalogussen/a522d30c-6c10-47fe-82e3-e9f524c14ca8",
            omschrijving="zaaktype2",
        )
        self.zaak_document2 = ZaakDocument(
            meta={"id": "a8c8bc90-defa-4548-bacd-793874c013ab"},
            url="https://api.zaken.nl/api/v1/zaken/a8c8bc90-defa-4548-bacd-793874c013ab",
            zaaktype=self.zaaktype_document2,
            identificatie="ZAAK-2022-000000105",
            bronorganisatie="7890",
            omschrijving="een hele mooie dikke omschrijving",
            vertrouwelijkheidaanduiding="confidentieel",
            va_order=20,
            rollen=[],
            eigenschappen={"tekst": {"Beleidsveld": "Integratie"}},
            deadline="2021-12-31",
        )
        self.zaak_document2.save()

        self.record_1 = ObjectRecordDocument(
            data=["de", "het", "een", "omschrijving", "2022"],
            geometry={},
        )
        self.object_document_1 = ObjectDocument(
            url="some-keywoird",
            object_type="https://api.zaken.nl/api/v1/zaken/a8c8bc90-defa-4548-bacd-793874c013ab",
            record=self.record_1,
            related_zaken=[],
        )
        self.object_document_1.save()

        self.eio_document_1 = InformatieObjectDocument(
            url="some-keyword",
            titel="some-titel_omsch_2022-20105.pdf(1)",
            related_zaken=[],
        )
        self.eio_document_1.save()
        self.refresh_index()

    def test_quick_search(self):
        import time

        time_then = time.time()
        results = quick_search("2022 omsch")
        print(f"QUERY TOOK {time.time()-time_then}")
        print(results["zaken"].__dict__)
        print("*" * 50)
        print(results["objecten"].__dict__)
        print("*" * 50)
        print(results["documenten"].__dict__)

        # from elasticsearch_dsl import Index

        # index = Index('documenten')
        # analysis = index.analyze(
        #     body={
        #         'text': "some-titel_omsch_2022-20-105.pdf(1)",
        #         'explain': False,
        #         'tokenizer': {
        #             'min_gram': 2,
        #             'max_gram': 12,
        #             'type': 'edge_ngram',
        #             'token_chars': ['letter', 'digit']
        #         },
        #         'filter': [
        #             'lowercase',
        #             {'stopwords': '_dutch_', 'type': 'stop'}
        #         ]
        #     }
        # )

        # for token in analysis['tokens']:
        #     print(token['token'])
