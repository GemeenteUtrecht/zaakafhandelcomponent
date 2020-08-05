from django.db.models import Prefetch

from rest_framework import viewsets

from ..models import Activity, Event
from .filters import ActivityFilter
from .serializers import ActivitySerializer


class ActivityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Activity.objects.order_by("created").prefetch_related(
        Prefetch("events", queryset=Event.objects.order_by("created"))
    )
    serializer_class = ActivitySerializer
    filterset_class = ActivityFilter
