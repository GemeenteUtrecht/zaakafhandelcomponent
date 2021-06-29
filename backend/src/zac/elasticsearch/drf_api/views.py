from typing import List

from django.utils.translation import gettext_lazy as _

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, views
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import GenericAPIView, ListCreateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

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


class SearchView(ESOrderingMixin, ESPaginationMixin, GenericAPIView):
    authentication_classes = (SessionAuthentication,)
    parser_classes = (IgnoreCamelCaseJSONParser,)
    permission_classes = (IsAuthenticated,)
    serializer_class = SearchSerializer

    def get_queryset(self, **kwargs):
        return search(**kwargs)

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
            "user": self.request.user,
            "ordering": ordering,
        }

        results = self.get_queryset(**search_query)
        page = self.paginate_queryset(results)
        serializer = ZaakDocumentSerializer(page, many=True)
        return self.get_paginated_response(
            serializer.data, fields=input_serializer.validated_data["fields"]
        )


class SearchReportViewSet(ESOrderingMixin, ListCreateAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = SearchReportSerializer
    queryset = SearchReport.objects.all()

    def get_queryset(self):
        qs = super().get_queryset()

        # filter on allowed zaaktypen
        zaaktypen = get_zaaktypen(self.request.user)
        allowed_zt_urls = {zt.url for zt in zaaktypen}

        # only allow reports where the zaaktypen are a sub-set of the accessible zaaktypen
        # for this particular user
        allowed_report_ids = []
        for report in qs:
            search_results = search(
                **{**report.query, "fields": ["zaaktype.url"]}, user=self.request.user
            )
            zaaktypen = set(result.zaaktype.url for result in search_results)
            if zaaktypen.issubset(allowed_zt_urls):
                allowed_report_ids.append(report.id)

        return qs.filter(id__in=allowed_report_ids)

    @extend_schema(
        summary=_("Create a search report"),
        request=SearchSerializer,
        parameters=[es_document_to_ordering_parameters(ZaakDocument)],
    )
    def post(self, request, *args, **kwargs):
        search_serializer = SearchSerializer(data=request.data)
        search_serializer.is_valid(raise_exception=True)

        # Get ordering
        ordering = ESOrderingFilter().get_ordering(request, self)

        # Make search query
        search_query = {
            **search_serializer.validated_data,
            "ordering": ordering,
        }

        # Create and save instance
        data = {
            **request.data,
            "query": search_query,
        }
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    @extend_schema(
        summary=_("Retrieve a list of search reports"),
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class SearchReportDetailView(ESOrderingMixin, ESPaginationMixin, GenericAPIView):
    parser_classes = (IgnoreCamelCaseJSONParser,)
    permission_classes = (IsAuthenticated & CanDownloadSearchReports,)
    queryset = SearchReport.objects.all()
    serializer_class = ZaakDocumentSerializer

    @extend_schema(
        operation_id="search_reports_detail",
        summary=_("Retrieve a search report"),
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

        results = search(user=request.user, **search_report.query)
        page = self.paginate_queryset(results)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(
            serializer.data, fields=search_report.query["fields"]
        )
