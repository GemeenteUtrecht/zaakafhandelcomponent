from django.db.models import Prefetch

from rest_framework import exceptions, mixins, permissions, viewsets

from zac.core.services import get_zaak

from ..models import Activity, Event
from .filters import ActivityFilter
from .permissions import CanReadZaakPermission, CanWritePermission
from .serializers import ActivitySerializer, EventSerializer


class ActivityViewSet(viewsets.ModelViewSet):
    queryset = Activity.objects.order_by("created").prefetch_related(
        Prefetch("events", queryset=Event.objects.order_by("created"))
    )
    permission_classes = (
        permissions.IsAuthenticated,
        CanReadZaakPermission | CanWritePermission,
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

            # permission check on the zaak itself
            zaak = get_zaak(zaak_url=zaak_url)
            if not self.request.user.has_perm("activities:read", zaak):
                raise exceptions.PermissionDenied(
                    "Not allowed to read activities for this zaak."
                )

        return qs


class EventViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = Event.objects.none()
    serializer_class = EventSerializer
    permission_classes = (permissions.IsAuthenticated, CanWritePermission)
    schema = None
