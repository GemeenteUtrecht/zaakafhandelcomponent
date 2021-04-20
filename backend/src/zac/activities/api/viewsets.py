from django.db.models import Prefetch

from rest_framework import mixins, permissions, viewsets

from ..models import Activity, Event
from .filters import ActivityFilter
from .permissions import CanReadOrWriteActivitiesPermission, CanWriteEventsPermission
from .serializers import ActivitySerializer, EventSerializer


class ActivityViewSet(viewsets.ModelViewSet):
    queryset = Activity.objects.order_by("created").prefetch_related(
        Prefetch("events", queryset=Event.objects.order_by("created"))
    )
    permission_classes = (
        permissions.IsAuthenticated,
        CanReadOrWriteActivitiesPermission,
    )
    serializer_class = ActivitySerializer
    filterset_class = ActivityFilter
    schema = None

    def filter_queryset(self, queryset):
        qs = super().filter_queryset(queryset)

        if self.action == "list":
            # for permission reasons, don't allow data retrieval without 'zaak' filter
            zaak_url = self.request.query_params.get("zaak")
            if not zaak_url:
                return queryset.none()

        return qs


class EventViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = Event.objects.none()
    serializer_class = EventSerializer
    permission_classes = (permissions.IsAuthenticated, CanWriteEventsPermission)
    schema = None
