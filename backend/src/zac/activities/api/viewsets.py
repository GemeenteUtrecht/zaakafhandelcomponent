from django.db.models import Prefetch
from django.utils.translation import gettext_lazy as _

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, permissions, viewsets
from rest_framework.response import Response

from ..models import Activity, Event
from .filters import ActivityFilter
from .permissions import (
    CanForceWriteActivitiesPermission,
    CanForceWriteEventsPermission,
    CanReadOrWriteActivitiesPermission,
    CanWriteEventsPermission,
)
from .serializers import (
    CreateOrUpdateActivitySerializer,
    EventSerializer,
    ReadActivitySerializer,
)


@extend_schema_view(
    list=extend_schema(
        summary=_("List activities."),
        parameters=[
            OpenApiParameter(
                name="zaak",
                required=True,
                type=OpenApiTypes.URI,
                description=_("URL-reference of the ZAAK related to the activities."),
                location=OpenApiParameter.QUERY,
            )
        ],
    ),
    retrieve=extend_schema(summary=_("Retrieve activity.")),
    create=extend_schema(summary=_("Create activity.")),
    partial_update=extend_schema(
        summary=_("Update activity."),
    ),
    destroy=extend_schema(summary=_("Destroy activity.")),
)
class ActivityViewSet(viewsets.ModelViewSet):
    queryset = (
        Activity.objects.order_by("created")
        .select_related("user_assignee")
        .select_related("group_assignee")
        .prefetch_related(
            Prefetch("events", queryset=Event.objects.order_by("created"))
        )
    )
    permission_classes = (
        permissions.IsAuthenticated,
        CanReadOrWriteActivitiesPermission,
        CanForceWriteActivitiesPermission,
    )
    filterset_class = ActivityFilter
    http_method_names = ["get", "post", "patch", "delete"]

    def filter_queryset(self, queryset):
        qs = super().filter_queryset(queryset)

        if self.action == "list":
            # for permission reasons, don't allow data retrieval without 'zaak' filter
            zaak_url = self.request.query_params.get("zaak")
            if not zaak_url:
                return queryset.none()

        return qs

    def get_serializer_class(self):
        mapping = {
            "GET": ReadActivitySerializer,
            "POST": CreateOrUpdateActivitySerializer,
            "PATCH": CreateOrUpdateActivitySerializer,
            "DELETE": CreateOrUpdateActivitySerializer,
        }
        return mapping.get(self.request.method, ReadActivitySerializer)

    def create(self, request, *args, **kwargs):
        if self.request.user.is_authenticated:
            self.request.data["created_by"] = self.request.user.pk
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(
            instance=instance, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)


@extend_schema_view(
    create=extend_schema(summary=_("Create event.")),
)
class EventViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = Event.objects.none()
    serializer_class = EventSerializer
    permission_classes = (
        permissions.IsAuthenticated,
        CanWriteEventsPermission,
        CanForceWriteEventsPermission,
    )

    def create(self, request, *args, **kwargs):
        if self.request.user.is_authenticated:
            self.request.data["created_by"] = self.request.user.username
        return super().create(request, *args, **kwargs)
