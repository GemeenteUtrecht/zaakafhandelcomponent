from django.conf import settings

from elasticsearch.exceptions import NotFoundError
from elasticsearch_dsl import Index


def check_if_index_exists(index=settings.ES_INDEX_ZAKEN):
    es_index = Index(index)
    if not es_index.exists():
        raise NotFoundError(
            404,
            "Couldn't find index: %s. Please try to create the index through a command first."
            % index,
        )
