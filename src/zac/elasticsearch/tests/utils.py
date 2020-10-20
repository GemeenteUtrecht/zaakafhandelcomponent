from django.conf import settings

from elasticsearch_dsl import Index


class ESMixin:
    def _create_index(self):
        zaken = Index(settings.ES_INDEX_ZAKEN)
        zaken.create(ignore=400)

    def _delete_index(self):
        zaken = Index(settings.ES_INDEX_ZAKEN)
        zaken.delete(ignore=404)

    def refresh_index(self):
        zaken = Index(settings.ES_INDEX_ZAKEN)
        zaken.refresh()

    def setUp(self):
        super().setUp()

        self._create_index()
        self.addCleanup(self._delete_index)
