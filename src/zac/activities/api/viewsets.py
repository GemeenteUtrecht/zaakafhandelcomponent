from rest_framework import viewsets

from ..models import Activity
from .filters import ActivityFilter
from .serializers import ActivitySerializer


class ActivityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Activity.objects.order_by("created")
    serializer_class = ActivitySerializer
    filterset_class = ActivityFilter
