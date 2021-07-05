from typing import List

from django.utils.translation import gettext_lazy as _

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, views
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import GenericAPIView, ListCreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from zac.api.drf_spectacular.utils import input_serializer_to_parameters
from zac.core.api.serializers import ZaakSerializer
from zac.core.services import get_zaaktypen

from ..documents import ZaakDocument
from ..models import SearchReport
from ..searches import autocomplete_zaak_search, search
from .filters import ESOrderingFilter
from .pagination import ESPagination
from .parsers import IgnoreCamelCaseJSONParser
from .permissions import CanDownloadSearchReports
from .serializers import (
    SearchReportSerializer,
    SearchSerializer,
    ZaakDocumentSerializer,
    ZaakIdentificatieSerializer,
)
from .utils import es_document_to_ordering_parameters


class GetZakenView(views.APIView):
    permission_classes = (IsAuthenticated,)

    @staticmethod
    def get_serializer(**kwargs):
        return ZaakSerializer(many=True, **kwargs)

    @extend_schema(
        summary=_("Autocomplete search zaken"),
        parameters=input_serializer_to_parameters(ZaakIdentificatieSerializer),
    )
    def get(self, request: Request) -> Response:
        """
        Retrieve a list of zaken based on autocomplete search.
        """
        serializer = ZaakIdentificatieSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        zaken = autocomplete_zaak_search(
            identificatie=serializer.validated_data["identificatie"]
        )
        zaak_serializer = self.get_serializer(instance=zaken)
        return Response(data=zaak_serializer.data)


class ESPaginationMixin:
    pagination_class = ESPagination

    def get_paginated_response(self, data, fields: List[str]):
        """
        Return a paginated style `Response` object for the given output data.
        """
        assert isinstance(self.pagination_class(), ESPagination)
        return self.paginator.get_paginated_response(data, fields)


class ESOrderingMixin:
    ordering = ("-identificatie",)
    search_document = ZaakDocument


class PerformSearchMixin:
    def perform_search(self, search_query):
        if search_query.get("zaaktype"):
            zaaktype_data = search_query.pop("zaaktype")
            zaaktypen = get_zaaktypen(
                self.request.user,
                catalogus=zaaktype_data["catalogus"],
                omschrijving=zaaktype_data["omschrijving"],
            )
            search_query["zaaktypen"] = [zaaktype.url for zaaktype in zaaktypen]

        results = search(user=self.request.user, **search_query)
        return results


class ESGenericAPIView(
    PerformSearchMixin, ESOrderingMixin, ESPaginationMixin, GenericAPIView
):
    pass


class SearchView(ESGenericAPIView):
    authentication_classes = (SessionAuthentication,)
    parser_classes = (IgnoreCamelCaseJSONParser,)
    permission_classes = (IsAuthenticated,)
    serializer_class = SearchSerializer

    def get_queryset(self, **kwargs):
        return self.perform_search(kwargs)

    @extend_schema(
        summary=_("Search zaken"),
        parameters=[
            es_document_to_ordering_parameters(ZaakDocument),
            OpenApiParameter(
                name="page",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Page of paginated response.",
            ),
        ],
        responses=ZaakDocumentSerializer(many=True),
    )
    def post(self, request, *args, **kwargs):
        """
        Retrieve a list of zaken based on input data.
        The response contains only zaken the user has permissions to see.

        """
        input_serializer = self.serializer_class(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        # Get ordering
        ordering = ESOrderingFilter().get_ordering(request, self)

        search_query = {
            **input_serializer.validated_data,
            "ordering": ordering,
        }

        results = self.get_queryset(**search_query)
        page = self.paginate_queryset(results)
        serializer = ZaakDocumentSerializer(page, many=True)
        return self.get_paginated_response(
            serializer.data, fields=input_serializer.validated_data["fields"]
        )


class SearchReportViewSet(PerformSearchMixin, ModelViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = SearchReportSerializer
    queryset = SearchReport.objects.all()

    def get_queryset(self):
        qs = super().get_queryset()

        # filter on allowed zaaktypen
        allowed_zts = get_zaaktypen(self.request.user)
        allowed_zt_urls = {zt.url for zt in allowed_zts}

        # only allow reports where the zaaktypen are a sub-set of the accessible zaaktypen
        # for this particular user
        allowed_report_ids = []
        for report in qs:
            search_results = self.perform_search(report.query)
            zaaktypen = {result.zaaktype.url for result in search_results}
            if zaaktypen.issubset(allowed_zt_urls):
                allowed_report_ids.append(report.id)

        return qs.filter(id__in=allowed_report_ids)

    @extend_schema(summary=_("Create a search report"))
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @extend_schema(summary=_("Destroy a search report"))
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @extend_schema(
        summary=_("Retrieve a list of search reports"),
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(summary=_("Partially update a search report"))
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(summary=_("Retrieve a search report"))
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(summary=_("Update a search report"))
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)


class SearchReportDetailView(ESGenericAPIView):
    parser_classes = (IgnoreCamelCaseJSONParser,)
    permission_classes = (IsAuthenticated & CanDownloadSearchReports,)
    queryset = SearchReport.objects.all()
    serializer_class = ZaakDocumentSerializer

    @extend_schema(
        operation_id="search_reports_results",
        summary=_("Retrieve the results of a search report"),
        parameters=[
            es_document_to_ordering_parameters(ZaakDocument),
            OpenApiParameter(
                name="page",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description="Page of paginated response.",
            ),
        ],
        responses=ZaakDocumentSerializer(many=True),
    )
    def get(self, request, *args, **kwargs):
        search_report = self.get_object()
        ordering = ESOrderingFilter().get_ordering(self.request, self)
        if ordering:
            search_report.query = {**search_report.query, "ordering": ordering}

        results = self.perform_search(search_report.query)
        page = self.paginate_queryset(results)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(
            serializer.data, fields=search_report.query["fields"]
        )
