from rest_framework import filters, viewsets

from zac.utils import pagination

from ..models import User
from .serializers import UserSerializer


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.filter(is_active=True)
    serializer_class = UserSerializer
    pagination_class = pagination.PageNumberPagination
    page_size = 100
    filter_backends = [filters.SearchFilter]
    search_fields = ["username", "first_name", "last_name"]
