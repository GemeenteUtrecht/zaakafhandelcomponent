from django.conf import settings

from elasticsearch_dsl import Index

from ..documents import ZaakDocument


class ESMixin:
    def _clear_index(self):
        zaken = Index(settings.ES_INDEX_ZAKEN)
        zaken.delete(ignore=404)
        ZaakDocument.init()

    def refresh_index(self):
        zaken = Index(settings.ES_INDEX_ZAKEN)
        zaken.refresh()

    def setUp(self):
        super().setUp()

        self._clear_index()
