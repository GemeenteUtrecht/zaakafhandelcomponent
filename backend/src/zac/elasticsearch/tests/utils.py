from django.conf import settings

from elasticsearch_dsl import Index
from zgw_consumers.api_models.base import factory

from zac.core.rollen import Rol
from zgw.models.zrc import Zaak

from ..api import append_rol_to_document, create_zaak_document
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
        print("1: ",zaak.uiterlijke_einddatum_afdoening)
        create_zaak_document(zaak)

    @staticmethod
    def add_rol_to_document(rol):
        if not isinstance(rol, Rol):
            rol = factory(Rol, rol)
        append_rol_to_document(rol)

    def setUp(self):
        super().setUp()

        self.clear_index(init=True)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

        cls.clear_index()
