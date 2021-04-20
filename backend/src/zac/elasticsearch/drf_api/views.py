from typing import List

from django.utils.translation import gettext_lazy as _

from drf_spectacular.utils import extend_schema
from rest_framework import authentication, permissions, views
from rest_framework.request import Request
from rest_framework.response import Response

from zac.api.drf_spectacular.utils import input_serializer_to_parameters
from zac.core.api.serializers import ZaakDetailSerializer, ZaakSerializer
from zac.core.services import get_zaaktypen, get_zaken_es
from zgw.models.zrc import Zaak

from ..documents import ZaakDocument
from ..searches import autocomplete_zaak_search
from .filters import ESOrderingFilter
from .parsers import IgnoreCamelCaseJSONParser
from .serializers import SearchSerializer, ZaakIdentificatieSerializer
from .utils import es_document_to_ordering_parameters


class GetZakenView(views.APIView):
    permission_classes = (permissions.IsAuthenticated,)

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


class SearchViewSet(views.APIView):
    parser_classes = (IgnoreCamelCaseJSONParser,)
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = SearchSerializer
    search_document = ZaakDocument
    ordering = (
        "-identificatie",
        "-startdatum",
        "-registratiedatum",
    )

    @extend_schema(
        summary=_("Search zaken"),
        parameters=[es_document_to_ordering_parameters(ZaakDocument)],
        responses=ZaakDetailSerializer(many=True),
    )
    def post(self, request, *args, **kwargs):
        """
        Retrieve a list of zaken based on input data.
        The response contains only zaken the user has permisisons to see.
        """
        input_serializer = self.serializer_class(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        # Get ordering
        ordering = ESOrderingFilter().get_ordering(request, self)
        zaken = self.perform_search({**input_serializer.data, "ordering": ordering})

        # TODO for now zaak.resultaat is str which is not supported by ZaakDetailSerializer
        for zaak in zaken:
            zaak.resultaat = None

        zaak_serializer = ZaakDetailSerializer(zaken, many=True)

        return Response(zaak_serializer.data)

    def perform_search(self, data) -> List[Zaak]:
        # TODO search on zaaktype attributes instead of urls
        if data.get("zaaktype"):
            zaaktype_data = data.pop("zaaktype")
            zaaktypen = get_zaaktypen(
                self.request.user,
                catalogus=zaaktype_data["catalogus"],
                omschrijving=zaaktype_data["omschrijving"],
            )
            data["zaaktypen"] = [zaaktype.url for zaaktype in zaaktypen]

        zaken = get_zaken_es(user=self.request.user, size=50, query_params=data)
        return zaken
