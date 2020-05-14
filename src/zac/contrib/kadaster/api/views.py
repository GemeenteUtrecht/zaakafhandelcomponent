import requests
from rest_framework import permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ..bag import Bag, LocationServer


class AdresSearchView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request: Request, *args, **kwargs):
        query = request.GET.get("q")
        if not query:
            return Response(
                {
                    "response": {"numFound": 0, "start": 0, "maxScore": 0, "docs": [],},
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

        return Response(results)


class PandFetchView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request: Request, *args, **kwargs):
        address_id = request.GET.get("id")
        if not address_id:
            return Response({"error": "missing ID"}, status=status.HTTP_400_BAD_REQUEST)

        location_server = LocationServer()
        resp_data = location_server.lookup(address_id)

        if not resp_data["numFound"] == 1:
            return Response(
                {"error": "Invalid ID provided"}, status=status.HTTP_400_BAD_REQUEST
            )

        doc = resp_data["docs"][0]
        vo_id = doc["adresseerbaarobject_id"]

        bag = Bag()

        verblijfsobject = bag.get(f"verblijfsobjecten/{vo_id}")
        panden = [
            pandrel["href"] for pandrel in verblijfsobject["_links"]["pandrelateringen"]
        ]
        assert len(panden) == 1

        pand = bag.retrieve(panden[0])

        data = {
            "adres": {
                "straatnaam": doc["straatnaam"],
                "nummer": doc["huisnummer"],
                "gemeentenaam": doc["gemeentenaam"],
                "postcode": doc.get("postcode", ""),
                "provincienaam": doc.get("provincienaam", ""),
            },
            "bagObject": {
                "url": pand["_links"]["self"]["href"],
                "geometrie": pand["_embedded"]["geometrie"],
                "oorspronkelijkBouwjaar": pand["oorspronkelijkBouwjaar"],
                "status": pand["status"],
            },
        }

        return Response(data)
