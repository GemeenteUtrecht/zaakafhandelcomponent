from django.utils.translation import gettext_lazy as _

from drf_spectacular.openapi import OpenApiParameter, OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ..processes import get_process_instances
from .serializers import ErrorSerializer, ProcessInstanceSerializer


class ProcessInstanceFetchView(APIView):
    schema_summary = _("List process instances for a zaak")
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
        """
        Get the Camunda process instances for a given zaak.

        Retrieve the process instances where the zaak URL is matches the process
        `zaakUrl` variable. Process instances return the available message that can be
        sent into the process and the available user tasks. The response includes the
        child-process instances of each matching process instance.
        """
        zaak_url = request.GET.get("zaak_url")
        if not zaak_url:
            err_serializer = ErrorSerializer(data={"error": "missing zaak_url"})
            return Response(err_serializer.data, status=status.HTTP_400_BAD_REQUEST)

        process_instances = get_process_instances(zaak_url)
        serializer = self.serializer_class(process_instances, many=True)

        return Response(serializer.data)
