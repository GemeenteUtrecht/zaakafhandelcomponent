from typing import List

from django.utils.translation import gettext_lazy as _

from drf_spectacular.utils import extend_schema
from rest_framework import authentication, permissions, views
from rest_framework.request import Request
from rest_framework.response import Response
from zgw_consumers.api_models.zaken import Zaak

from zac.accounts.permissions import UserPermissions
from zac.api.drf_spectacular.utils import input_serializer_to_parameters
from zac.core.api.serializers import ZaakDetailSerializer, ZaakSerializer
from zac.core.services import get_zaaktypen, get_zaken_es

from ..searches import autocomplete_zaak_search
from .parsers import IgnoreCamelCaseJSONParser
from .serializers import SearchSerializer, ZaakIdentificatieSerializer


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

    @extend_schema(summary=_("Search zaken"), responses=ZaakDetailSerializer(many=True))
    def post(self, request, *args, **kwargs):
        """
        Retrieve a list of zaken based on input data.
        The response contains only zaken the user has permisisons to see.
        """
        input_serializer = self.serializer_class(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        zaken = self.perform_search(input_serializer.data)
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
