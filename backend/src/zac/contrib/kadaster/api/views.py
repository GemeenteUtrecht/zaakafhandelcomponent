from django.utils.translation import gettext_lazy as _

import requests
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ..bag import Bag, LocationServer
from .serializers import (
    BagLocationSerializer,
    PandSerializer,
    VerblijfsobjectSerializer,
)


class AdresSearchView(APIView):
    serializer_class = BagLocationSerializer
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
            return Response(
                {
                    "response": {
                        "numFound": 0,
                        "maxScore": 0,
                        "docs": [],
                    },
                    "highlighting": {},
                    "spellcheck": {},
                }
            )

        location_server = LocationServer()
        try:
            results = location_server.suggest(
                {"q": query, "fq": "bron:bag AND type:adres"}
            )
        except requests.HTTPError as exc:
            status_code = getattr(
                exc.response, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            return Response({"error": exc.args[0]}, status=status_code)

        return Response(self.serializer_class(results).data)


class BagObjectFetchView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get_address(self, address_id: str) -> dict:
        location_server = LocationServer()
        resp_data = location_server.lookup(address_id)

        return resp_data

    def get_bag_object(self, address: dict):
        return NotImplementedError(
            "Subclasses of BagObjectFetchView must provide a get_bag_object() method."
        )

    def get_bag_data(self, bag_object: dict) -> dict:
        return {
            "url": bag_object["_links"]["self"]["href"],
            "geometrie": bag_object["_embedded"]["geometrie"],
            "status": bag_object["status"],
        }

    def get(self, request: Request, *args, **kwargs):
        address_id = request.GET.get("id")
        if not address_id:
            return Response({"error": "missing ID"}, status=status.HTTP_400_BAD_REQUEST)

        address = self.get_address(address_id)
        if not address["numFound"] == 1:
            return Response(
                {"error": "Invalid ID provided"}, status=status.HTTP_400_BAD_REQUEST
            )
        doc = address["docs"][0]
        bag_object = self.get_bag_object(doc)
        bag_data = self.get_bag_data(bag_object)

        data = {
            "adres": {
                "straatnaam": doc["straatnaam"],
                "nummer": doc["huisnummer"],
                "gemeentenaam": doc["gemeentenaam"],
                "postcode": doc.get("postcode", ""),
                "provincienaam": doc.get("provincienaam", ""),
            },
            "bagObject": bag_data,
        }
        return Response(self.serializer_class(data).data)


class PandFetchView(BagObjectFetchView):
    serializer_class = PandSerializer

    def get_bag_object(self, address):
        vo_id = address["adresseerbaarobject_id"]
        bag = Bag()

        verblijfsobject = bag.get(f"verblijfsobjecten/{vo_id}")

        panden = [
            pandrel["href"] for pandrel in verblijfsobject["_links"]["pandrelateringen"]
        ]
        assert len(panden) == 1

        pand = bag.retrieve(panden[0])

        return pand

    def get_bag_data(self, bag_object: dict) -> dict:
        data = super().get_bag_data(bag_object)
        data["oorspronkelijkBouwjaar"] = bag_object["oorspronkelijkBouwjaar"]
        return data

    @extend_schema(
        summary=_("Retrieve pand from BAG API."),
        parameters=[
            OpenApiParameter(
                "id",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description=_(
                    "The ID of the BAG object. Can be found using the BAG address suggestions."
                ),
                required=True,
            )
        ],
    )
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)


class VerblijfsobjectFetchView(BagObjectFetchView):
    serializer_class = VerblijfsobjectSerializer

    def get_bag_object(self, address):
        vo_id = address["adresseerbaarobject_id"]
        bag = Bag()

        verblijfsobject = bag.get(f"verblijfsobjecten/{vo_id}")

        return verblijfsobject

    def get_bag_data(self, bag_object: dict) -> dict:
        data = super().get_bag_data(bag_object)
        data["oppervlakte"] = bag_object["oppervlakte"]
        return data

    @extend_schema(
        summary=_("Retrieve verblijfsobject from BAG API."),
        parameters=[
            OpenApiParameter(
                "id",
                OpenApiTypes.STR,
                OpenApiParameter.QUERY,
                description=_(
                    "The ID of the BAG object. Can be found using the BAG address suggestions."
                ),
                required=True,
            )
        ],
    )
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)
