from rest_framework.pagination import PageNumberPagination


class BffPagination(PageNumberPagination):
    page_size = 100
