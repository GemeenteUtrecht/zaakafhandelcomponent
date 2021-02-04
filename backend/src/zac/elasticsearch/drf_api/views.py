from django.utils.translation import gettext_lazy as _

from drf_spectacular.utils import extend_schema
from rest_framework import permissions, views
from rest_framework.request import Request
from rest_framework.response import Response

from zac.api.drf_spectacular.utils import input_serializer_to_parameters
from zac.core.api.serializers import ZaakSerializer

from ..searches import autocomplete_zaak_search
from .serializers import ZaakIdentificatieSerializer


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
