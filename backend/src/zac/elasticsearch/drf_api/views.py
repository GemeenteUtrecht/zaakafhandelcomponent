from typing import List

from django.utils.translation import gettext_lazy as _

from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import views
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.viewsets import ModelViewSet

from zac.accounts.api.permissions import HasTokenAuth
from zac.accounts.authentication import ApplicationTokenAuthentication
from zac.api.drf_spectacular.utils import input_serializer_to_parameters
from zac.core.api.serializers import ZaakSerializer
from zac.core.services import get_zaaktypen

from ..documents import ZaakDocument
from ..models import SearchReport
from ..searches import autocomplete_zaak_search, search
from .filters import ESOrderingFilter
from .pagination import ESPagination
from .parsers import IgnoreCamelCaseJSONParser
from .serializers import (
    SearchReportSerializer,
    SearchSerializer,
    ZaakDocumentSerializer,
    ZaakIdentificatieSerializer,
)
from .utils import es_document_to_ordering_parameters


class GetZakenView(views.APIView):
    authentication_classes = [
        ApplicationTokenAuthentication
    ] + api_settings.DEFAULT_AUTHENTICATION_CLASSES
    permission_classes = (HasTokenAuth | IsAuthenticated,)

    @staticmethod
    def get_serializer(**kwargs):
        return ZaakSerializer(many=True, **kwargs)

    @extend_schema(
        summary=_("Autocomplete search ZAAKen."),
        parameters=input_serializer_to_parameters(ZaakIdentificatieSerializer),
    )
    def get(self, request: Request) -> Response:
        """
        Retrieve a list of zaken based on autocomplete search.
        """
        serializer = ZaakIdentificatieSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        zaken = autocomplete_zaak_search(
            request=request,
            identificatie=serializer.validated_data["identificatie"],
        )
        zaak_serializer = self.get_serializer(instance=zaken)
        return Response(data=zaak_serializer.data)


class PerformSearchMixin:
    def perform_search(self, search_query):
        if search_query.get("zaaktype"):
            zaaktype_data = search_query.pop("zaaktype")

            # First get zaaktypen based on omschrijving...
            zaaktypen = get_zaaktypen(
                self.request,
                catalogus=zaaktype_data["catalogus"],
                omschrijving=zaaktype_data["omschrijving"],
            )

            # ...because omschrijving can change, we will then also
            # fetch all the zaaktypen with the same identificatie(s) as the
            # zaaktypen which matched the omschrijving.
            urls = []
            identificaties = {zt.identificatie for zt in zaaktypen}
            for identificatie in identificaties:
                urls += [
                    zt.url
                    for zt in get_zaaktypen(
                        self.request,
                        catalogus=zaaktype_data["catalogus"],
                        identificatie=identificatie,
                    )
                ]

            search_query["zaaktypen"] = [url for url in set(urls)]

        results = search(**search_query, request=self.request)
        return results


class SearchView(PerformSearchMixin, views.APIView):
    authentication_classes = [
        ApplicationTokenAuthentication
    ] + api_settings.DEFAULT_AUTHENTICATION_CLASSES
    ordering = ("-identificatie",)
    parser_classes = (IgnoreCamelCaseJSONParser,)
    permission_classes = (HasTokenAuth | IsAuthenticated,)
    search_document = ZaakDocument
    serializer_class = SearchSerializer
    pagination_class = ESPagination

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
        summary=_("Search for ZAAKen in Elasticsearch."),
        parameters=[
            es_document_to_ordering_parameters(ZaakDocument),
            OpenApiParameter(
                name="page",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description=_("Page of paginated response."),
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

        results = self.perform_search(search_query)
        page = self.paginate_results(results)
        serializer = ZaakDocumentSerializer(page, many=True)
        return self.get_paginated_response(
            serializer.data, input_serializer.validated_data["fields"]
        )


@extend_schema_view(
    create=extend_schema(summary=_("Create search report.")),
    destroy=extend_schema(summary=_("Destroy search report.")),
    list=extend_schema(
        summary=_("List search reports."),
    ),
    partial_update=extend_schema(summary=_("Partially update search report.")),
    retrieve=extend_schema(summary=_("Retrieve search report.")),
    update=extend_schema(summary=_("Update search report.")),
    results=extend_schema(
        operation_id="search_reports_results",
        summary=_("Retrieve search report results."),
        parameters=[
            es_document_to_ordering_parameters(ZaakDocument),
            OpenApiParameter(
                name="page",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description=_("Page of paginated response."),
            ),
        ],
        responses=ZaakDocumentSerializer(many=True),
    ),
)
class SearchReportViewSet(PerformSearchMixin, ModelViewSet):
    ordering = ("-identificatie",)
    permission_classes = (IsAuthenticated,)
    queryset = SearchReport.objects.all()
    search_document = ZaakDocument
    serializer_class = SearchReportSerializer

    def get_paginated_response(self, *args):
        assert isinstance(self.paginator, ESPagination)
        return self.paginator.get_paginated_response(*args)

    @action(
        detail=True,
        pagination_class=ESPagination,
    )
    def results(self, request, *args, **kwargs):
        search_report = self.get_object()
        ordering = ESOrderingFilter().get_ordering(self.request, self)
        if ordering:
            search_report.query = {**search_report.query, "ordering": ordering}

        results = self.perform_search(search_report.query)
        page = self.paginate_queryset(results)
        serializer = ZaakDocumentSerializer(page, many=True)
        return self.get_paginated_response(
            serializer.data, search_report.query["fields"]
        )
