from typing import List

from django.utils.translation import ugettext_lazy as _

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import authentication
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from zac.core.services import get_zaaktypen
from zac.elasticsearch.drf_api.pagination import ESPagination
from zac.elasticsearch.drf_api.serializers import ZaakDocumentSerializer
from zac.elasticsearch.drf_api.views import PerformSearchMixin
from zac.elasticsearch.searches import count_by_zaaktype

from ..models import Board, BoardItem
from .filters import BoardItemFilter
from .pagination import DashboardPagination
from .permissions import (
    CanForceUseBoardItem,
    CanReadManagementDashboard,
    CanUseBoardItem,
)
from .serializers import (
    BoardItemSerializer,
    BoardSerializer,
    ManagementDashboardSerializer,
    SummaryManagementDashboardSerializer,
)


@extend_schema_view(
    list=extend_schema(summary=_("List boards.")),
    retrieve=extend_schema(summary=_("Retrieve board.")),
)
class BoardViewSet(ReadOnlyModelViewSet):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Board.objects.prefetch_related("columns").order_by("-modified")
    serializer_class = BoardSerializer
    lookup_field = "uuid"


@extend_schema_view(
    list=extend_schema(summary=_("List board items.")),
    retrieve=extend_schema(summary=_("Retrieve board item.")),
    create=extend_schema(summary=_("Create board item.")),
    update=extend_schema(summary=_("Update board item.")),
    partial_update=extend_schema(summary=_("Patch board item.")),
    destroy=extend_schema(summary=_("Delete board item.")),
)
class BoardItemViewSet(ModelViewSet):
    authentication_classes = [SessionAuthentication]
    permission_classes = [IsAuthenticated, CanUseBoardItem, CanForceUseBoardItem]
    queryset = BoardItem.objects.select_related("column", "column__board").order_by(
        "-pk"
    )
    serializer_class = BoardItemSerializer
    filterset_class = BoardItemFilter
    lookup_field = "uuid"

    def get_queryset(self):
        base = super().get_queryset()

        if self.action != "list":
            return base

        return base.for_user(self.request)


class ManagementDashboardDetailView(PerformSearchMixin, APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (
        IsAuthenticated,
        CanReadManagementDashboard,
    )
    pagination_class = DashboardPagination
    serializer_class = ManagementDashboardSerializer

    @property
    def paginator(self):
        """
        The paginator instance associated with the view, or `None`.

        """
        if not hasattr(self, "_paginator"):
            if self.pagination_class is None:
                self._paginator = None
            else:
                self._paginator = self.pagination_class()
        return self._paginator

    def paginate_results(self, results):
        return self.paginator.paginate_queryset(results, self.request, view=self)

    def get_paginated_response(self, data, fields: List[str]):
        """
        Return a paginated style `Response` object for the given output data.
        """
        assert isinstance(self.pagination_class(), ESPagination)
        return self.paginator.get_paginated_response(data, fields)

    @extend_schema(
        summary=_(
            "Retrieve active ZAAKs by their ZAAKTYPE. Results only include ZAAKs of allowed ZAAKTYPEs."
        ),
        request=ManagementDashboardSerializer,
        responses={200: ZaakDocumentSerializer},
    )
    def post(self, request: Request, *args, **kwargs):
        input_serializer = self.serializer_class(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        results = self.perform_search(input_serializer.validated_data)

        page = self.paginate_results(results)
        serializer = ZaakDocumentSerializer(page, many=True)
        return self.get_paginated_response(
            serializer.data, input_serializer.validated_data["fields"]
        )


class ManagementDashboardSummaryView(APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (
        IsAuthenticated,
        CanReadManagementDashboard,
    )
    serializer_class = SummaryManagementDashboardSerializer

    @extend_schema(
        summary=_(
            "Retrieves the summary for the management dashboard. Results are sorted alphabetically on ZAAKTYPE `omschrijving`."
        ),
        request=None,
        responses={200: SummaryManagementDashboardSerializer(many=True)},
    )
    def post(self, request, *args, **kwargs):
        results = count_by_zaaktype(request=request)

        # For presentation purposes separate zaaktypen
        # by catalogus and map identificatie to omschrijving.
        zts = get_zaaktypen()
        catalogi = {zt.catalogus for zt in zts}
        zts_per_catalogus = {}
        for catalogus in catalogi:
            zts_per_catalogus[catalogus] = list(
                filter(lambda zt: zt.catalogus == catalogus, zts)
            )

        for catalogus in catalogi:
            max_versiedatum_per_zaaktype = {}
            for zt in (zts := zts_per_catalogus[catalogus]):
                if old_zt_versiedatum := max_versiedatum_per_zaaktype.get(
                    zt.identificatie
                ):
                    if zt.versiedatum > old_zt_versiedatum:
                        max_versiedatum_per_zaaktype[zt.identificatie] = zt.versiedatum
                else:
                    max_versiedatum_per_zaaktype[zt.identificatie] = zt.versiedatum
            zts_per_catalogus[catalogus] = {
                zt.identificatie: zt.omschrijving
                for zt in zts
                if zt.versiedatum == max_versiedatum_per_zaaktype[zt.identificatie]
            }

        serializer = self.serializer_class(
            results,
            many=True,
            context={"zaaktypen": zts_per_catalogus},
        )

        return Response(sorted(serializer.data, key=lambda zts: zts["catalogus"]))
