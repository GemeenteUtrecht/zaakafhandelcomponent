from rest_framework import filters, viewsets

from zac.utils import pagination

from ..models import User
from .serializers import UserSerializer


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserSerializer
    pagination_class = pagination.PageNumberPagination
    page_size = 100
    filter_backends = [filters.SearchFilter]
    search_fields = ["username", "first_name", "last_name"]

    def get_queryset(self):
        filter_users = self.request.query_params.get("filter_users", "")
        queryset = User.objects.filter(is_active=True)
        if filter_users:
            # Custom cleaning of query_parameter
            # TODO find better implementation
            filter_users = filter_users.split(",")
            return queryset.exclude(id__in=filter_users)
        else:
            return queryset
