from django.db import transaction
from django.utils.translation import gettext_lazy as _

from django_filters import rest_framework as django_filter
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters, mixins, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from zac.core.api.pagination import BffPagination
from zac.utils.mixins import PatchModelMixin

from ..models import AccessRequest, User, UserAtomicPermission
from .filters import UserFilter
from .permissions import CanCreateOrHandleAccessRequest, CanGrantAccess
from .serializers import (
    AccessRequestDetailSerializer,
    AtomicPermissionSerializer,
    CreateAccessRequestSerializer,
    GrantPermissionSerializer,
    HandleAccessRequestSerializer,
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
    partial_update=extend_schema(
        summary=_("Handle an access request"),
        request=HandleAccessRequestSerializer,
        responses={200: HandleAccessRequestSerializer},
    ),
)
class AccessRequestViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    PatchModelMixin,
    viewsets.GenericViewSet,
):
    """
    Access request for a particular zaak
    """

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, CanCreateOrHandleAccessRequest]
    queryset = AccessRequest.objects.all()

    def get_serializer_class(self):
        mapping = {
            "GET": AccessRequestDetailSerializer,
            "POST": CreateAccessRequestSerializer,
            "PATCH": HandleAccessRequestSerializer,
        }
        return mapping[self.request.method]


@extend_schema_view(
    retrieve=extend_schema(summary=_("Retrieve atomic permission")),
    create=extend_schema(
        summary=_("Grant atomic permission to zaak"),
        request=GrantPermissionSerializer,
        responses={201: GrantPermissionSerializer},
    ),
    destroy=extend_schema(summary=_("Delete atomic permission")),
)
class AtomicPermissionViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Create and delete an atomic permission for a particular user
    """

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, CanGrantAccess]
    queryset = UserAtomicPermission.objects.select_related("user", "atomic_permission")
    serializer_class = AtomicPermissionSerializer

    def get_serializer_class(self):
        mapping = {
            "GET": AtomicPermissionSerializer,
            "POST": GrantPermissionSerializer,
            "DELETE": AtomicPermissionSerializer,
        }
        return mapping[self.request.method]

    @transaction.atomic
    def perform_destroy(self, instance):
        atomic_permission = instance.atomic_permission

        super().perform_destroy(instance)

        # remove permission if there are no users using it
        if not atomic_permission.useratomicpermission_set.count():
            atomic_permission.delete()
