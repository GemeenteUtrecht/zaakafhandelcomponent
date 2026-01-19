from typing import Any, Callable, Dict, Iterable, List

from django.core.exceptions import ImproperlyConfigured
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
from zac.contrib.dowc.api import check_document_status
from zac.core.api.permissions import CanListZaakDocuments, CanReadZaken
from zac.core.api.serializers import ZaakSerializer
from zac.core.api.views import GetZaakMixin
from zac.core.services import get_zaaktypen

from ..documents import InformatieObjectDocument, ZaakDocument
from ..models import SearchReport
from ..searches import (
    autocomplete_zaak_search,
    quick_search,
    search_informatieobjects,
    search_zaken,
    usage_report_informatieobjecten,
    usage_report_zaken,
)
from .filters import ESOrderingFilter
from .pagination import ESPagination
from .parsers import IgnoreCamelCaseJSONParser
from .serializers import (
    ESListZaakDocumentSerializer,
    QuickSearchResultSerializer,
    QuickSearchSerializer,
    SearchInformatieObjectSerializer,
    SearchReportSerializer,
    SearchSerializer,
    VGUReportInputSerializer,
    VGUReportIOSerializer,
    VGUReportZakenSerializer,
    ZaakDocumentSerializer,
    ZaakIdentificatieSerializer,
)
from .utils import es_document_to_ordering_parameters

# ---------- Helpers / Mixins ----------


class PerformSearchMixin:
    def perform_search(self, search_query):
        if search_query.get("zaaktype"):
            zaaktype_data = search_query.pop("zaaktype")
            zaaktypen = get_zaaktypen(
                self.request,
                catalogus=zaaktype_data["catalogus"],
                omschrijving=zaaktype_data["omschrijving"],
            )
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
            zaaktypen = [url for url in set(urls)]

            # In case someone does not have the right blueprint permissions
            # let search_zaken filter out what is allowed and what is not.
            search_query["zaaktypen"] = zaaktypen

        results = search_zaken(
            **search_query, request=self.request, only_allowed=True, return_search=True
        )
        return results


class PaginatedSearchMixin:
    search_document = None

    @property
    def search_document(self):
        """
        Return the configured ES document class.
        """
        if not hasattr(self, "_search_document"):
            if not self.search_document:
                raise ImproperlyConfigured(
                    "PaginatedSearchMixin needs a search_document attribute."
                )
            else:
                self._search_document = self.search_document
        return self._search_document

    @property
    def paginator(self):
        """
        The paginator instance associated with the view, or `None`.
        """
        if not hasattr(self, "_paginator"):
            if self.pagination_class is None:
                self._paginator = None
            else:
                self._paginator = self.pagination_class(view=self)
        return self._paginator

    def paginate_results(self, results) -> List:
        return self.paginator.paginate_queryset(results, self.request, view=self)

    def get_paginated_response(self, data, fields: List[str]):
        """
        Return a paginated style `Response` object for the given output data.
        """
        assert isinstance(self.pagination_class(view=self), ESPagination)
        return self.paginator.get_paginated_response(data, fields)


# ---------- Views ----------


class GetZakenView(views.APIView):
    authentication_classes = [
        ApplicationTokenAuthentication
    ] + api_settings.DEFAULT_AUTHENTICATION_CLASSES
    permission_classes = (HasTokenAuth | IsAuthenticated,)

    @extend_schema(
        summary=_("Autocomplete search ZAAKen."),
        parameters=input_serializer_to_parameters(ZaakIdentificatieSerializer),
        request=ZaakIdentificatieSerializer,
        responses={200: ZaakSerializer(many=True)},
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
        return Response(ZaakSerializer(instance=zaken, many=True).data)


class SearchView(PerformSearchMixin, PaginatedSearchMixin, views.APIView):
    authentication_classes = [
        ApplicationTokenAuthentication
    ] + api_settings.DEFAULT_AUTHENTICATION_CLASSES
    permission_classes = (HasTokenAuth | IsAuthenticated,)
    parser_classes = (IgnoreCamelCaseJSONParser,)

    ordering = ("-identificatie.keyword",)
    search_document = ZaakDocument
    serializer_class = SearchSerializer
    pagination_class = ESPagination

    @extend_schema(
        summary=_("Search for ZAAKen in elasticsearch."),
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

        search = self.perform_search(
            {
                **input_serializer.validated_data,
                "ordering": ordering,
            }
        )
        page = self.paginate_results(search)
        serializer = ZaakDocumentSerializer(page, many=True)
        return self.get_paginated_response(
            serializer.data, input_serializer.validated_data["fields"]
        )


class QuickSearchView(views.APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = QuickSearchSerializer

    @extend_schema(
        summary=_(
            "Quick search through ZAAKs, INFORMATIEOBJECTs and OBJECTs in elasticsearch."
        ),
        responses=QuickSearchResultSerializer,
    )
    def post(self, request, *args, **kwargs):
        """
        Retrieve a list of zaken, objecten and documenten based on input data.
        Only returns data the user is allowed to see.
        Results are capped to 15 per type.
        """
        input_serializer = self.serializer_class(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        results = quick_search(
            input_serializer.validated_data["search"],
            only_allowed=True,
            request=request,
        )
        return Response(QuickSearchResultSerializer(results).data)


@extend_schema_view(
    create=extend_schema(summary=_("Create search report.")),
    destroy=extend_schema(summary=_("Destroy search report.")),
    list=extend_schema(summary=_("List search reports.")),
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
class SearchReportViewSet(PerformSearchMixin, PaginatedSearchMixin, ModelViewSet):
    permission_classes = (IsAuthenticated,)
    queryset = SearchReport.objects.all()
    serializer_class = SearchReportSerializer
    ordering = ("-identificatie.keyword",)
    search_document = ZaakDocument

    @action(detail=True, pagination_class=ESPagination)
    def results(self, request, *args, **kwargs):
        search_report = self.get_object()
        ordering = ESOrderingFilter().get_ordering(self.request, self)
        if ordering:
            search_report.query["ordering"] = ordering

        search = self.perform_search(search_report.query)
        page = self.paginate_queryset(search)
        serializer = ZaakDocumentSerializer(page, many=True)
        return self.get_paginated_response(
            serializer.data, search_report.query["fields"]
        )


class ListZaakDocumentsESView(GetZaakMixin, PaginatedSearchMixin, views.APIView):
    permission_classes = (IsAuthenticated, CanReadZaken, CanListZaakDocuments)
    ordering = ("titel.keyword",)
    serializer_class = SearchInformatieObjectSerializer
    pagination_class = ESPagination
    page_size = 10
    search_document = InformatieObjectDocument

    def get_object(self):
        # Avoid multiple permission checks etc.
        if not hasattr(self, "_object"):
            self._object = super().get_object()
        return self._object

    @extend_schema(
        summary=_("Retrieve INFORMATIEOBJECTs for ZAAK in Elasticsearch."),
        description=_("Default ordered on `titel`."),
        parameters=[
            es_document_to_ordering_parameters(InformatieObjectDocument),
            OpenApiParameter(
                name="page",
                type=int,
                location=OpenApiParameter.QUERY,
                required=False,
                description=_("Page of paginated response."),
            ),
            OpenApiParameter(
                name="pageSize",
                type=int,
                location=OpenApiParameter.QUERY,
                default=10,
                description=_("Page size of paginated response."),
            ),
        ],
        responses=ESListZaakDocumentSerializer(many=True),
    )
    def post(self, request, *args, **kwargs):
        """
        Retrieve a list of INFORMATIEOBJECTs voor ZAAK based on input data.

        """
        zaak = self.get_object()
        input_serializer = self.serializer_class(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        ordering = ESOrderingFilter().get_ordering(request, self)

        search = search_informatieobjects(
            **input_serializer.validated_data,
            ordering=ordering,
            zaak=zaak.url,
            return_search=True,
        )
        page = list(self.paginate_results(search))

        open_documenten = check_document_status(documents=[doc.url for doc in page])
        serializer = ESListZaakDocumentSerializer(
            page,
            many=True,
            context={
                "open_documenten": {dowc.document: dowc for dowc in open_documenten},
                "zaak_is_closed": bool(zaak.einddatum),
                "request": request,
            },
        )
        return self.get_paginated_response(
            serializer.data, input_serializer.validated_data["fields"]
        )


# ---------- VGU Reports ----------


class VGUBaseView(views.APIView):
    authentication_classes = [ApplicationTokenAuthentication]
    permission_classes = (HasTokenAuth,)
    serializer_class = VGUReportInputSerializer
    report_fn: Callable[..., Iterable[Dict[str, Any]]] = None
    response_serializer_class = None

    def run_report(self, start_period, end_period):
        if self.report_fn is None:
            raise NotImplementedError("Subclasses must set `report_fn`.")
        return self.report_fn(start_period=start_period, end_period=end_period)

    def serialize_response(self, results_iterable):
        if self.response_serializer_class is None:
            raise NotImplementedError(
                "Subclasses must set `response_serializer_class`."
            )
        return self.response_serializer_class(results_iterable, many=True)

    def post(self, request: Request, *args, **kwargs):
        input_serializer = self.serializer_class(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        start_period = input_serializer.validated_data["start_period"]
        end_period = input_serializer.validated_data["end_period"]

        results = self.run_report(start_period, end_period)
        serializer = self.serialize_response(results)
        return Response(serializer.data)


class VGUReportZakenView(VGUBaseView):
    report_fn = staticmethod(usage_report_zaken)
    response_serializer_class = VGUReportZakenSerializer

    @extend_schema(
        summary=_("Retrieve a custom VGU zaak report based on input period."),
        responses=VGUReportZakenSerializer,
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class VGUReportInformatieObjectenView(VGUBaseView):
    report_fn = staticmethod(usage_report_informatieobjecten)
    response_serializer_class = VGUReportIOSerializer

    @extend_schema(
        summary=_(
            "Retrieve a custom VGU informatieobjecten report based on input period."
        ),
        responses=VGUReportIOSerializer,
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)
