from zac.core.api.pagination import BffPagination


class WorkstackPagination(BffPagination):
    page_size = 20
    max_page_size = 100
