from django.db.models import Prefetch
from django.utils.translation import gettext_lazy as _

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import exceptions, mixins, permissions, viewsets
from rest_framework.response import Response

from zac.core.services import get_zaak

from ..models import Activity, Event
from .filters import ActivityFilter
from .permissions import CanReadZaakPermission, CanWritePermission
from .serializers import ActivitySerializer, EventSerializer, PatchActivitySerializer


@extend_schema_view(
    list=extend_schema(
        summary=_("List activities"),
        parameters=[
            OpenApiParameter(
                name="zaak",
                required=True,
                type=OpenApiTypes.URI,
                description=_("The url of the case related to the activities."),
                location=OpenApiParameter.QUERY,
            )
        ],
    ),
    retrieve=extend_schema(summary=_("Retrieve activity")),
    create=extend_schema(summary=_("Create activity")),
    partial_update=extend_schema(
        summary=_("Update activity"),
        request=PatchActivitySerializer,
        responses={201: ActivitySerializer},
    ),
    destroy=extend_schema(summary=_("Destroy activity")),
)
class ActivityViewSet(viewsets.ModelViewSet):
    queryset = (
        Activity.objects.order_by("created")
        .select_related("assignee")
        .prefetch_related(
            Prefetch("events", queryset=Event.objects.order_by("created"))
        )
    )
    permission_classes = (
        permissions.IsAuthenticated,
        CanReadZaakPermission | CanWritePermission,
    )
    filterset_class = ActivityFilter
    http_method_names = ["get", "post", "patch", "delete"]

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return PatchActivitySerializer
        return ActivitySerializer

    def filter_queryset(self, queryset):
        qs = super().filter_queryset(queryset)

        if self.action == "list":
            # for permission reasons, don't allow data retrieval without 'zaak' filter
            zaak_url = self.request.query_params.get("zaak")
            if not zaak_url:
                return queryset.none()

            # permission check on the zaak itself
            zaak = get_zaak(zaak_url=zaak_url)
            if not self.request.user.has_perm("activities:read", zaak):
                raise exceptions.PermissionDenied(
                    "Not allowed to read activities for this zaak."
                )

        return qs

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(
            instance=instance, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, "_prefetched_objects_cache", None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        serializer = ActivitySerializer(instance=instance, context={"request": request})
        return Response(serializer.data)


@extend_schema_view(
    create=extend_schema(summary=_("Create event")),
)
class EventViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = Event.objects.none()
    serializer_class = EventSerializer
    permission_classes = (permissions.IsAuthenticated, CanWritePermission)
