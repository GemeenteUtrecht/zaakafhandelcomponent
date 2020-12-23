from django_filters import rest_framework as django_filter
from rest_framework import filters, viewsets

from zac.utils import pagination

from ..models import User
from .filters import UserFilter
from .serializers import UserSerializer


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all().order_by("username")
    serializer_class = UserSerializer
    pagination_class = pagination.PageNumberPagination
    page_size = 100
    filter_backends = (
        filters.SearchFilter,
        django_filter.DjangoFilterBackend,
    )
    search_fields = ["username", "first_name", "last_name"]
    filterset_class = UserFilter
    schema = None
