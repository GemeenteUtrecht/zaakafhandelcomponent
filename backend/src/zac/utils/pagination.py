from rest_framework import pagination


class PageNumberPagination(pagination.PageNumberPagination):
    def paginate_queryset(self, queryset, request, view=None):
        if view and hasattr(view, "page_size"):
            self.page_size = view.page_size
        return super().paginate_queryset(queryset, request, view=view)
