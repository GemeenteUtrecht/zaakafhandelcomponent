from typing import List, Optional

from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.generics import GenericAPIView, ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from zac.core.api.pagination import BffPagination
from zac.core.services import get_zaaktypen
from zac.elasticsearch.documents import ZaakDocument
from zac.elasticsearch.drf_api.filters import ESOrderingFilter
from zac.elasticsearch.drf_api.utils import es_document_to_ordering_parameters

from ..export import get_zaken_details_for_export
from ..models import Report
from .data import ReportRow
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
            description="Possible sorting parameters. Multiple values are possible and should be separated by a comma.",
            enum=(
                "identificatie",
                "omschrijving",
                "startdatum",
                "zaaktype.omschrijving",
            ),
        )
    ],
)
class ReportDownloadView(GenericAPIView):
    permission_classes = (IsAuthenticated,)
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

    def get_object(self) -> Optional[Report]:
        pk = self.kwargs.get("pk")
        report = get_object_or_404(Report, pk=pk) if pk else None
        return report

    def get_queryset(self) -> List[Optional[ReportRow]]:
        report = self.get_object()
        if not report:
            return [None]

        ordering = ESOrderingFilter().get_ordering(self.request, self)
        zaken, zaak_statuses, zaak_eigenschappen = get_zaken_details_for_export(
            report, ordering=ordering
        )

        qs = []
        for zaak in zaken:
            eigenschappen = zaak_eigenschappen.get(zaak.url) or ""
            if eigenschappen:
                formatted = [
                    f"{eigenschap.naam}: {eigenschap.waarde}"
                    for eigenschap in sorted(eigenschappen, key=lambda e: e.naam)
                ]
                eigenschappen = "\n".join(formatted)

            qs.append(
                ReportRow(
                    identificatie=zaak.identificatie,
                    zaaktype_omschrijving=zaak.zaaktype.omschrijving,
                    startdatum=zaak.startdatum,
                    omschrijving=zaak.omschrijving,
                    eigenschappen=eigenschappen,
                    status=zaak_statuses[zaak.url] if zaak.status else "",
                )
            )
        return qs

    def get(self, request, *args, **kwargs):
        qs = self.get_queryset()
        page = self.paginate_queryset(qs)
        serializer = self.serializer_class(page, many=True)
        return self.get_paginated_response(serializer.data)

    def has_permission(self):
        # move logic from "reports:download" rule
        report = self.get_object()
        if not report:
            return True

        zaaktypen = get_zaaktypen(self.request.user)
        identificaties = {zt.identificatie for zt in zaaktypen}
        return set(report.zaaktypen).issubset(identificaties)
