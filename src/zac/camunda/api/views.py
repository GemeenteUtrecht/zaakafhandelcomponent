from rest_framework import permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ..processes import get_process_instances
from .serializers import ProcessInstanceSerializer


class ProcessInstanceFetchView(APIView):
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request: Request, *args, **kwargs):
        zaak_url = request.GET.get("zaak_url")
        if not zaak_url:
            return Response(
                {"error": "missing zaak_url"}, status=status.HTTP_400_BAD_REQUEST
            )

        process_instances = get_process_instances(zaak_url)
        serializer = ProcessInstanceSerializer(process_instances, many=True)

        return Response(serializer.data)
