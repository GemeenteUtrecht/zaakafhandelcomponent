from django.utils.translation import gettext_lazy as _

from django_filters import rest_framework as django_filter
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, mixins, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from zac.core.api.pagination import BffPagination

from ..models import AccessRequest, User
from .filters import UserFilter
from .permissions import CanRequestAccess
from .serializers import (
    AccessRequestDetailSerializer,
    CreateAccessRequestSerializer,
    UserSerializer,
)


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


@extend_schema_view(
    retrieve=extend_schema(summary=_("Retrieve access requests")),
    create=extend_schema(
        summary=_("Create an access request"),
        request=CreateAccessRequestSerializer,
        responses={201: CreateAccessRequestSerializer},
    ),
)
class AccessRequestViewSet(
    mixins.CreateModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """
    Access request for a particular zaak
    """

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, CanRequestAccess]
    queryset = AccessRequest.objects.all()

    def get_serializer_class(self):
        mapping = {
            "GET": AccessRequestDetailSerializer,
            "POST": CreateAccessRequestSerializer,
        }
        return mapping[self.request.method]
