from drf_spectacular.openapi import OpenApiParameter, OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from zac.core.services import get_zaak

from ..processes import get_process_instances
from .serializers import ErrorSerializer, ProcessInstanceSerializer


class ProcessInstanceFetchView(APIView):
    serializer_class = ProcessInstanceSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "zaak_url",
                OpenApiTypes.URI,
                OpenApiParameter.QUERY,
                required=True,
            )
        ],
        responses={
            200: serializer_class(many=True),
            400: ErrorSerializer,
        },
    )
    def get(self, request: Request, *args, **kwargs):
        zaak_url = request.GET.get("zaak_url")
        if not zaak_url:
            err_serializer = ErrorSerializer(data={"error": "missing zaak_url"})
            return Response(err_serializer.data, status=status.HTTP_400_BAD_REQUEST)

        zaak = get_zaak(zaak_url=zaak_url)
        process_instances = get_process_instances(zaak_url)
        serializer = self.serializer_class(
            process_instances, many=True, context={"zaak": zaak}
        )

        return Response(serializer.data)
