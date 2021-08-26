from django.utils.translation import ugettext_lazy as _

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from ..models import Board, BoardItem
from .filters import BoardItemFilter
from .serializer import BoardItemSerializer, BoardSerializer


@extend_schema_view(
    list=extend_schema(summary=_("List boards")),
    retrieve=extend_schema(summary=_("Retrieve board")),
)
class BoardViewSet(ReadOnlyModelViewSet):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Board.objects.prefetch_related("columns").order_by("-modified")
    serializer_class = BoardSerializer
    lookup_field = "uuid"


@extend_schema_view(
    list=extend_schema(summary=_("List board items")),
    retrieve=extend_schema(summary=_("Retrieve board item")),
    create=extend_schema(summary=_("Create board item")),
    update=extend_schema(summary=_("Update board item")),
    partial_update=extend_schema(summary=_("Patch board item")),
    destroy=extend_schema(summary=_("Delete board item")),
)
class BoardItemViewSet(ModelViewSet):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = BoardItem.objects.select_related("column", "column__board").order_by(
        "-pk"
    )
    serializer_class = BoardItemSerializer
    filterset_class = BoardItemFilter
    lookup_field = "uuid"
