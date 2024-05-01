from zac.core.api.pagination import BffPagination
from zac.elasticsearch.drf_api.pagination import ESPagination


class WorkstackPagination(BffPagination):
    page_size = 20
    max_page_size = 100


class ESWorkStackPagination(ESPagination):
    page_size = 20
    max_page_size = 100
