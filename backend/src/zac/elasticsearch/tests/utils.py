from django.conf import settings

from elasticsearch_dsl import Index
from zgw_consumers.api_models.base import factory
from zgw_consumers.api_models.catalogi import ZaakType

from zgw.models.zrc import Zaak

from ..api import create_zaak_document, create_zaaktype_document
from ..documents import ZaakDocument


class ESMixin:
    @staticmethod
    def clear_index(init=False):
        zaken = Index(settings.ES_INDEX_ZAKEN)
        zaken.delete(ignore=404)
        if init:
            ZaakDocument.init()

    @staticmethod
    def refresh_index():
        zaken = Index(settings.ES_INDEX_ZAKEN)
        zaken.refresh()

    @staticmethod
    def create_zaak_document(zaak):
        if not isinstance(zaak, Zaak):
            zaak = factory(Zaak, zaak)
        return create_zaak_document(zaak)

    @staticmethod
    def create_zaaktype_document(zaaktype):
        if not isinstance(zaaktype, ZaakType):
            zaaktype = factory(ZaakType, zaaktype)
        return create_zaaktype_document(zaaktype)

    def setUp(self):
        super().setUp()

        self.clear_index(init=True)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

        cls.clear_index()
