from django.utils.translation import gettext_lazy as _

from django_filters import rest_framework as django_filter
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, viewsets
from rest_framework.decorators import action

from zac.core.api.pagination import BffPagination

from ..models import User
from .filters import UserFilter
from .serializers import UserSerializer


@extend_schema_view(
    list=extend_schema(summary=_("List user accounts")),
    retrieve=extend_schema(summary=_("Retrieve user account")),
)
class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all().order_by("username")
    serializer_class = UserSerializer
    pagination_class = BffPagination
    filter_backends = (
        filters.SearchFilter,
        django_filter.DjangoFilterBackend,
    )
    search_fields = ["username", "first_name", "last_name"]
    filterset_class = UserFilter

    @extend_schema(summary=_("Current logged in user"))
    @action(detail=False)
    def me(self, request, *args, **kwargs):
        self.kwargs["pk"] = self.request.user.id
        return self.retrieve(request, *args, **kwargs)
