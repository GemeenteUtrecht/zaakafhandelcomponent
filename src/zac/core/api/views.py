from rest_framework import exceptions, views
from rest_framework.request import Request
from rest_framework.response import Response

from ..services import fetch_zaaktype, get_informatieobjecttypen_for_zaaktype, get_zaak
from .serializers import InformatieObjectTypeSerializer


class GetInformatieObjectTypenView(views.APIView):

    # TODO: permissions checks on zaak - can this user read/mutate the zaak?

    def get(self, request: Request) -> Response:
        zaak_url = request.query_params.get("zaak")
        if not zaak_url:
            raise exceptions.ValidationError("'zaak' query parameter is required.")

        zaak = get_zaak(zaak_url=zaak_url)
        zaak.zaaktype = fetch_zaaktype(zaak.zaaktype)
        informatieobjecttypen = get_informatieobjecttypen_for_zaaktype(zaak.zaaktype)

        serializer = InformatieObjectTypeSerializer(informatieobjecttypen, many=True)
        return Response(serializer.data)
