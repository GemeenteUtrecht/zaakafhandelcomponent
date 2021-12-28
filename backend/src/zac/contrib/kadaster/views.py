from django.utils.translation import gettext_lazy as _

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import permissions, serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .api import get_address_suggestions, get_pand, get_verblijfsobject
from .serializers import (
    AddressSearchResponseSerializer,
    PandSerializer,
    VerblijfsobjectSerializer,
)


class AdresSearchView(APIView):
    serializer_class = AddressSearchResponseSerializer
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(
        summary=_("List BAG address suggestions"),
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
        query = request.GET.get("q")
        if not query:
            raise serializers.ValidationError(_("Missing query parameter 'q'"))

        instances = get_address_suggestions(query)
        serializer = self.serializer_class(instance=instances)
        return Response(serializer.data)


class PandFetchView(APIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = PandSerializer

    @extend_schema(
        summary=_("Retrieve pand from BAG API."),
        parameters=[
            OpenApiParameter(
                "id",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description=_(
                    "The ID of the BAG object. The ID can be found using the BAG address suggestions."
                ),
                required=True,
            )
        ],
    )
    def get(self, request: Request, *args, **kwargs):
        address_id = request.GET.get("id")
        if not address_id:
            raise serializers.ValidationError(_("Missing query parameter 'id'"))

        instance = get_pand(address_id)
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
                    "The ID of the BAG object. The ID can be found using the BAG address suggestions."
                ),
                required=True,
            )
        ],
    )
    def get(self, request: Request, *args, **kwargs):
        address_id = request.GET.get("id")
        if not address_id:
            raise serializers.ValidationError(_("Missing query parameter 'id'"))

        instance = get_verblijfsobject(address_id)
        serializer = self.serializer_class(instance=instance)
        return Response(serializer.data)
