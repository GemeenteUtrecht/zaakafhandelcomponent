from zac.elasticsearch.drf_api.pagination import ESPagination


class DashboardPagination(ESPagination):
    page_size_query_param = "page_size"
    page_size = 20
