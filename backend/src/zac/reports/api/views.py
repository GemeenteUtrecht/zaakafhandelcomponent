from django.utils.translation import gettext_lazy as _

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.permissions import IsAuthenticated

from zac.core.api.pagination import BffPagination
from zac.core.services import get_zaaktypen
from zac.elasticsearch.documents import ZaakDocument
from zac.elasticsearch.drf_api.filters import ESOrderingFilter

from ..export import get_zaken_details_for_export
from ..models import Report
from .permissions import CanDownloadReports
from .serializers import ReportDownloadSerializer, ReportSerializer


@extend_schema(summary=_("List reports"))
class ReportListViewSet(ListAPIView):
    queryset = Report.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = ReportSerializer

    def get_queryset(self):
        qs = super().get_queryset()

        # filter on allowed zaaktypen
        zaaktypen = get_zaaktypen(self.request.user)
        identificaties = list({zt.identificatie for zt in zaaktypen})

        # only allow reports where the zaaktypen are a sub-set of the accessible zaaktypen
        # for this particular user
        return qs.filter(zaaktypen__contained_by=identificaties)


@extend_schema(
    summary=_("Retrieve report"),
    parameters=[
        OpenApiParameter(
            name="ordering",
            type=str,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Possible ordering parameters. Multiple values are possible and should be separated by a comma.",
            enum=(
                "identificatie",
                "omschrijving",
                "startdatum",
                "zaaktype.omschrijving",
            ),
        ),
        OpenApiParameter(
            name="page",
            type=int,
            location=OpenApiParameter.QUERY,
            required=False,
            description="Page of paginated response.",
        ),
    ],
)
class ReportDownloadView(GenericAPIView):
    queryset = Report.objects.all()
    permission_classes = (IsAuthenticated & CanDownloadReports,)
    serializer_class = ReportDownloadSerializer
    pagination_class = BffPagination
    search_document = ZaakDocument
    ordering = (
        "identificatie",
        "startdatum",
    )
    ordering_fields = (
        "identificatie",
        "omschrijving",
        "startdatum",
        "zaaktype.omschrijving",
    )

    def get(self, request, *args, **kwargs):
        report = self.get_object()
        ordering = ESOrderingFilter().get_ordering(self.request, self)
        zaken = get_zaken_details_for_export(request.user, report, ordering=ordering)
        page = self.paginate_queryset(zaken)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)
