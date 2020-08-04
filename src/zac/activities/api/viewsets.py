from djangorestframework_camel_case.render import (
    CamelCaseBrowsableAPIRenderer,
    CamelCaseJSONRenderer,
)
from rest_framework import permissions, viewsets

from ..models import Activity
from .serializers import ActivitySerializer


class ActivityViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = (
        permissions.IsAuthenticated,
    )  # TODO: proper permission filtering
    # TODO: make default renderer class
    renderer_classes = (
        CamelCaseBrowsableAPIRenderer,
        CamelCaseJSONRenderer,
    )
    queryset = Activity.objects.all()
    serializer_class = ActivitySerializer
