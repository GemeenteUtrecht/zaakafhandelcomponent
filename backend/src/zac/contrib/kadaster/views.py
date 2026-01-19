from django.conf import settings
from django.utils.translation import gettext_lazy as _

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from zac.api.utils import remote_schema_ref

from .api import (
    find_pand,
    get_address_suggestions,
    get_nummeraanduiding,
    get_pand,
    get_verblijfsobject,
)
from .serializers import (
    AddressSearchResponseSerializer,
    FindPandSerializer,
    NummerAanduidingenSerializer,
    PandenSerializer,
    VerblijfsobjectSerializer,
)


class AdresSearchView(APIView):
    serializer_class = AddressSearchResponseSerializer
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(
        summary=_("List BAG address suggestions."),
        parameters=[
            OpenApiParameter(
                "q",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description=_(
                    "The search query. The Solr-syntax can be used, for example: combining searches with `and` or using double quotes for sequenced searches. Searches are allowed to be incomplete and you can use synonyms."
                ),
                required=True,
            )
        ],
    )
    def get(self, request: Request, *args, **kwargs):
        """
        This endpoint allows users to search for address(es) (suggestions) using the PDOK locatieserver. The `id` of the address(es) can then be used to fetch a pand or a verblijfsobject from the BAG API.

        Please see https://www.pdok.nl/restful-api/-/article/pdok-locatieserver-1 for more details on how to use the PDOK locatieserver API and how to query for address suggestions.
        Be cognizant of the fact that we only allow use of the `q` query parameter. The API request the ZAC makes to the locatieserver will have the  `fq=bron:bag AND type:adres` query parameter and its value added to every request.
        """
        query = request.GET.get("q")
        if not query:
            raise serializers.ValidationError(_("Missing query parameter 'q'"))

        instances = get_address_suggestions(query)
        serializer = self.serializer_class(instance=instances)
        return Response(serializer.data)


class FindPand(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = FindPandSerializer

    @extend_schema(
        summary=_("Find pand in the BAG API."),
        parameters=[
            OpenApiParameter(
                "id",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description=_(
                    "The `id` of the BAG object. The `id` can be found using the BAG address suggestions."
                ),
                required=True,
            )
        ],
    )
    def get(self, request: Request, *args, **kwargs):
        """
        This endpoint allows users to fetch a pand and relevant metadata from the BAG API.

        Once users have retrieved the `id` of an address from the PDOK locatieserver, they can use the `id` to fetch a pand from the BAG API.
        Please see https://github.com/lvbag/BAG-API for further documentation on the BAG API.
        """
        address_id = request.GET.get("id")
        if not address_id:
            raise serializers.ValidationError(_("Missing query parameter 'id'"))

        instance = find_pand(address_id)
        serializer = self.serializer_class(instance=instance)
        return Response(serializer.data)


class PandView(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = PandenSerializer

    @extend_schema(
        summary=_("Retrieve pand from BAG API."),
        parameters=[
            OpenApiParameter(
                "pandidentificatie",
                OpenApiTypes.STR,
                OpenApiParameter.PATH,
                description=_("The `pandidentificatie` of the pand object."),
                required=True,
            )
        ],
        responses={
            (200, "application/json"): remote_schema_ref(
                settings.EXTERNAL_API_SCHEMAS["BAG_API_SCHEMA"],
                ["components", "schemas", "Pand"],
            ),
        },
    )
    def get(self, request: Request, pandidentificatie: str):
        """
        This endpoint allows users to get a pand based on the `pandidentificatie`.

        Please see https://github.com/lvbag/BAG-API for further documentation on the BAG API.
        """

        instance = get_pand(pandidentificatie)
        serializer = self.serializer_class(instance=instance)
        return Response(serializer.data)


class NummerAanduidingView(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = NummerAanduidingenSerializer

    @extend_schema(
        summary=_("Retrieve nummeraanduiding from BAG API."),
        parameters=[
            OpenApiParameter(
                "nummeraanduidingidentificatie",
                OpenApiTypes.STR,
                OpenApiParameter.PATH,
                description=_(
                    "The `nummeraanduidingidentificatie` of the nummeraanduiding object."
                ),
                required=True,
            )
        ],
        responses={
            (200, "application/json"): remote_schema_ref(
                settings.EXTERNAL_API_SCHEMAS["BAG_API_SCHEMA"],
                ["components", "schemas", "Nummeraanduiding"],
            ),
        },
    )
    def get(self, request: Request, nummeraanduidingidentificatie: str):
        """
        This endpoint allows users to get `nummeraanduidingen` based on the `nummeraanduidingidentificatie`.

        Please see https://github.com/lvbag/BAG-API for further documentation on the BAG API.
        """

        instance = get_nummeraanduiding(nummeraanduidingidentificatie)
        serializer = self.serializer_class(instance=instance)
        return Response(serializer.data)


class VerblijfsobjectFetchView(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = VerblijfsobjectSerializer

    @extend_schema(
        summary=_("Retrieve verblijfsobject from BAG API."),
        parameters=[
            OpenApiParameter(
                "id",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description=_(
                    "The `id` of the BAG object. The `id` can be found using the BAG address suggestions."
                ),
                required=True,
            )
        ],
    )
    def get(self, request: Request, *args, **kwargs):
        """
        This endpoint allows users to fetch a verblijfsobject and relevant metadata from the BAG API.

        Once users have retrieved the `id` of an address from the PDOK locatieserver, they can use the `id` to fetch a verblijfsobject from the BAG API.
        Please see https://github.com/lvbag/BAG-API for further documentation on the BAG API.
        """
        address_id = request.GET.get("id")
        if not address_id:
            raise serializers.ValidationError(_("Missing query parameter 'id'"))

        instance = get_verblijfsobject(address_id)
        serializer = self.serializer_class(instance=instance)
        return Response(serializer.data)
