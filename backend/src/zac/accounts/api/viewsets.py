from django.contrib.auth.models import Group
from django.db import transaction
from django.db.models import Prefetch
from django.utils.translation import gettext_lazy as _

from django_filters import rest_framework as django_filter
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import filters, mixins, status, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.settings import api_settings

from zac.core.api.pagination import BffPagination
from zac.utils.mixins import PatchModelMixin

from ..authentication import ApplicationTokenAuthentication
from ..constants import AccessRequestResult
from ..email import send_email_to_requester
from ..models import (
    AccessRequest,
    AuthorizationProfile,
    BlueprintPermission,
    Role,
    User,
    UserAtomicPermission,
    UserAuthorizationProfile,
)
from .filters import (
    UserAtomicPermissionFilterSet,
    UserAuthorizationProfileFilterSet,
    UserFilterSet,
)
from .permissions import (
    CanCreateOrHandleAccessRequest,
    CanForceCreateOrHandleAccessRequest,
    CanForceGrantAccess,
    CanGrantAccess,
    HasTokenAuth,
    ManageGroup,
)
from .serializers import (
    AccessRequestDetailSerializer,
    AtomicPermissionSerializer,
    AuthProfileSerializer,
    CreateAccessRequestSerializer,
    GrantPermissionSerializer,
    GroupSerializer,
    HandleAccessRequestSerializer,
    ManageGroupSerializer,
    ReadUserAuthorizationProfileSerializer,
    RoleSerializer,
    UpdateGrantPermissionSerializer,
    UserAuthorizationProfileSerializer,
    UserSerializer,
)
from .utils import group_permissions


@extend_schema_view(
    list=extend_schema(summary=_("List user accounts.")),
    retrieve=extend_schema(summary=_("Retrieve user account.")),
)
class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.prefetch_related("groups").all().order_by("username")
    serializer_class = UserSerializer
    pagination_class = BffPagination
    filter_backends = (
        filters.SearchFilter,
        django_filter.DjangoFilterBackend,
    )
    authentication_classes = [
        ApplicationTokenAuthentication
    ] + api_settings.DEFAULT_AUTHENTICATION_CLASSES
    permission_classes = (HasTokenAuth | IsAuthenticated,)
    search_fields = ["username", "first_name", "last_name", "email"]
    filterset_class = UserFilterSet

    @extend_schema(summary=_("Retrieve current logged in user."))
    @action(detail=False)
    def me(self, request, *args, **kwargs):
        self.kwargs["pk"] = self.request.user.id
        return self.retrieve(request, *args, **kwargs)


@extend_schema_view(
    list=extend_schema(summary=_("List user groups.")),
    retrieve=extend_schema(summary=_("Retrieve a user group.")),
    create=extend_schema(summary=_("Create a user group.")),
    update=extend_schema(summary=_("Update a user group.")),
    destroy=extend_schema(summary=_("Delete a user group.")),
    partial_update=extend_schema(exclude=True),
)
class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.prefetch_related("user_set").all().order_by("name")
    pagination_class = BffPagination
    filter_backends = (filters.SearchFilter,)
    search_fields = ["name"]
    permission_classes = [IsAuthenticated, ManageGroup]
    allowed_methods = ["get", "put", "post", "delete"]
    serializer_class = ManageGroupSerializer

    def get_serializer_class(self):
        mapping = {"GET": {"list": GroupSerializer}}
        return mapping.get(self.request.method, {}).get(
            self.action, ManageGroupSerializer
        )

    def perform_create(self, serializer):
        group = serializer.save()
        self.request.user.manages_groups.add(group)


@extend_schema_view(
    retrieve=extend_schema(summary=_("Retrieve access requests.")),
    create=extend_schema(
        summary=_("Create an access request."),
        request=CreateAccessRequestSerializer,
        responses={201: CreateAccessRequestSerializer},
    ),
    partial_update=extend_schema(
        summary=_("Handle an access request."),
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
    permission_classes = [
        IsAuthenticated,
        CanCreateOrHandleAccessRequest,
        CanForceCreateOrHandleAccessRequest,
    ]
    queryset = AccessRequest.objects.all()

    def get_serializer_class(self):
        mapping = {
            "GET": AccessRequestDetailSerializer,
            "POST": CreateAccessRequestSerializer,
            "PATCH": HandleAccessRequestSerializer,
        }
        return mapping[self.request.method]


@extend_schema_view(
    retrieve=extend_schema(summary=_("Retrieve atomic permission.")),
    list=extend_schema(
        summary=_("List user atomic permissions related to object."),
        parameters=[
            OpenApiParameter(
                name="object_url",
                required=True,
                type=OpenApiTypes.URI,
                description=_(
                    "URL-reference of object related to user atomic permissions."
                ),
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="username",
                required=True,
                type=OpenApiTypes.STR,
                description=_("Username of user related to user atomic permissions."),
                location=OpenApiParameter.QUERY,
            ),
        ],
        request=AtomicPermissionSerializer(many=True),
        responses={200: AtomicPermissionSerializer(many=True)},
    ),
    create=extend_schema(
        summary=_("Grant atomic permission to ZAAK."),
        request=GrantPermissionSerializer(many=True),
        responses={201: GrantPermissionSerializer(many=True)},
    ),
    destroy=extend_schema(summary=_("Delete atomic permission.")),
)
class AtomicPermissionViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Manage atomic permissions for a user.

    """

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, CanGrantAccess, CanForceGrantAccess]
    queryset = UserAtomicPermission.objects.select_related("user", "atomic_permission")
    serializer_class = AtomicPermissionSerializer
    filterset_class = UserAtomicPermissionFilterSet
    allowed_methods = ["get", "put", "post", "delete"]

    def get_serializer(self, *args, **kwargs):
        mapping = {
            "GET": AtomicPermissionSerializer,
            "PUT": UpdateGrantPermissionSerializer,
            "POST": GrantPermissionSerializer,
            "DELETE": AtomicPermissionSerializer,
        }
        if self.request.method in ["POST", "PUT"]:
            kwargs.update({"many": True})
        return mapping[self.request.method](*args, **kwargs)

    def filter_queryset(self, queryset):
        """
        Only filter on list action

        """
        if self.action != "list":
            self.filterset_class = None
        return super().filter_queryset(queryset)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        user_atomic_permission = serializer.instance[0]
        headers = self.get_success_headers(serializer.data)

        # send email
        transaction.on_commit(
            lambda: send_email_to_requester(
                user_atomic_permission.user,
                zaak_url=user_atomic_permission.atomic_permission.object_url,
                result=AccessRequestResult.approve,
                request=request,
            )
        )
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary=_("Partially update multiple user atomic permissions."),
        request=UpdateGrantPermissionSerializer(many=True),
        responses={200: AtomicPermissionSerializer(many=True)},
    )
    @action(
        methods=["put"],
        detail=False,
        permission_classes=[IsAuthenticated, CanGrantAccess, CanForceGrantAccess],
        url_name="update",
    )
    @transaction.atomic
    def bulk_update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        qs = self.get_queryset()
        qs.filter(
            user=serializer.validated_data[0]["user"],
            atomic_permission__object_url=serializer.validated_data[0][
                "atomic_permission"
            ]["object_url"],
        ).actual().delete()
        self.perform_create(serializer)

        user_atomic_permission = serializer.instance[0]
        # send email
        transaction.on_commit(
            lambda: send_email_to_requester(
                user_atomic_permission.user,
                zaak_url=user_atomic_permission.atomic_permission.object_url,
                result=AccessRequestResult.approve,
                request=request,
            )
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    @transaction.atomic
    def perform_destroy(self, instance):
        atomic_permission = instance.atomic_permission
        user = instance.user
        zaak = atomic_permission.object_url

        super().perform_destroy(instance)

        # remove permission if there are no users using it
        if not atomic_permission.useratomicpermission_set.count():
            atomic_permission.delete()

        # send email about losing the access to the user
        transaction.on_commit(
            lambda: send_email_to_requester(
                user,
                zaak_url=zaak,
                result=AccessRequestResult.reject,
                request=self.request,
            )
        )


@extend_schema_view(
    list=extend_schema(summary=_("List authorization profiles.")),
    retrieve=extend_schema(summary=_("Retrieve authorization profile.")),
    create=extend_schema(summary=_("Create authorization profile.")),
    update=extend_schema(summary=_("Update authorization profile.")),
    destroy=extend_schema(summary=_("Delete authorization profile.")),
)
class AuthProfileViewSet(viewsets.ModelViewSet):
    """
    This view assumes the user can only select object_type == zaak and
    adds the relevant INFORMATIEOBJECTTYPEs (related to ZAAKTYPE) policies with
    the same `vertrouwelijkheidaanduiding` as the ZAAKTYPE policies.

    """

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, IsAdminUser]
    queryset = AuthorizationProfile.objects.prefetch_related(
        Prefetch(
            "blueprint_permissions",
            queryset=BlueprintPermission.objects.select_related("role").all(),
        )
    ).all()
    serializer_class = AuthProfileSerializer
    lookup_field = "uuid"
    http_method_names = ["get", "post", "put", "delete"]

    def get_object(self):
        obj = super().get_object()
        permissions = obj.blueprint_permissions.select_related("role").all()
        obj.group_permissions = group_permissions(permissions)
        return obj

    def get_queryset(self):
        qs = super().get_queryset()
        if self.action == "list":
            for auth_profile in qs:
                auth_profile.group_permissions = group_permissions(
                    auth_profile.blueprint_permissions.all()
                )

        return qs


@extend_schema_view(
    list=extend_schema(summary=_("List roles.")),
    retrieve=extend_schema(summary=_("Retrieve role.")),
    create=extend_schema(summary=_("Create role.")),
    update=extend_schema(summary=_("Update role.")),
    destroy=extend_schema(summary=_("Destroy role.")),
)
class RoleViewSet(
    viewsets.ModelViewSet,
):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, IsAdminUser]
    queryset = Role.objects.all()
    serializer_class = RoleSerializer

    def get_serializer(self, *args, **kwargs):
        """
        Return the serializer instance that should be used for validating and
        deserializing input, and for serializing output.
        """
        serializer_class = self.get_serializer_class()
        kwargs.setdefault("context", self.get_serializer_context())
        serializer = serializer_class(*args, **kwargs)
        if kwargs.get("many", False):
            serializer.child.set_permissions_choices()
        else:
            serializer.set_permissions_choices()

        return serializer


@extend_schema_view(
    list=extend_schema(summary=_("List user authorization profiles.")),
    retrieve=extend_schema(summary=_("Retrieve user authorization profile.")),
    create=extend_schema(summary=_("Create user authorization profile.")),
    partial_update=extend_schema(
        summary=_("Partially update user authorization profile.")
    ),
    update=extend_schema(summary=_("Update user authorization profile.")),
    destroy=extend_schema(summary=_("Delete user authorization profile.")),
)
class UserAuthorizationProfileViewSet(viewsets.ModelViewSet):
    """
    A filter is *required* on list request and ignored on all other requests.

    """

    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, IsAdminUser]
    queryset = (
        UserAuthorizationProfile.objects.prefetch_related(
            Prefetch(
                "user",
                queryset=User.objects.defer("atomic_permissions", "auth_profiles")
                .prefetch_related(
                    Prefetch("manages_groups", queryset=Group.objects.all())
                )
                .prefetch_related(Prefetch("groups", queryset=Group.objects.all()))
                .all(),
            )
        )
        .prefetch_related(
            Prefetch(
                "auth_profile",
                queryset=AuthorizationProfile.objects.all(),
            )
        )
        .all()
        .order_by("user", "auth_profile")
    )
    pagination_class = BffPagination
    filter_backends = [filters.OrderingFilter, DjangoFilterBackend]
    filterset_class = UserAuthorizationProfileFilterSet
    ordering_fields = ["user", "auth_profile"]
    filter_fields = ["user", "auth_profile", "is_active"]

    def get_serializer_class(self):
        mapping = {
            "GET": ReadUserAuthorizationProfileSerializer,
            "POST": UserAuthorizationProfileSerializer,
            "PUT": UserAuthorizationProfileSerializer,
            "PATCH": UserAuthorizationProfileSerializer,
            "DELETE": UserAuthorizationProfileSerializer,
        }
        return mapping[self.request.method]

    def filter_queryset(self, queryset):
        """
        Only filter on list action

        """
        if self.action != "list":
            self.filterset_class = None
        return super().filter_queryset(queryset)
