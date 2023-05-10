from rest_framework.pagination import PageNumberPagination


class BffPagination(PageNumberPagination):
    page_size = 100


class ObjectsPagination(PageNumberPagination):
    page_size_query_param = "pageSize"
    page_size = 20
