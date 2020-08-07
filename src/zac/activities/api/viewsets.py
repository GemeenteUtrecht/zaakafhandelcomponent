from django.db.models import Prefetch

from rest_framework import mixins, viewsets

from ..models import Activity, Event
from .filters import ActivityFilter
from .serializers import ActivitySerializer, EventSerializer


class ActivityViewSet(viewsets.ModelViewSet):
    # TODO: add/check permissions!
    #   - can create activities
    #   - can create activities for given zaak(type)
    queryset = Activity.objects.order_by("created").prefetch_related(
        Prefetch("events", queryset=Event.objects.order_by("created"))
    )
    serializer_class = ActivitySerializer
    filterset_class = ActivityFilter


class EventViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = Event.objects.none()
    serializer_class = EventSerializer
