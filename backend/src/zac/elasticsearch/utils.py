from django.conf import settings

from elasticsearch.exceptions import NotFoundError
from elasticsearch_dsl import Index


def check_if_index_exists():
    zaken = Index(settings.ES_INDEX_ZAKEN)
    if not zaken.exists():
        raise NotFoundError(
            404,
            "Couldn't find index: %s. Please try to run index_zaken first."
            % settings.ES_INDEX_ZAKEN,
        )
