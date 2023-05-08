from rest_framework.pagination import PageNumberPagination


class WorkstackPagination(PageNumberPagination):
    page_size = 20
