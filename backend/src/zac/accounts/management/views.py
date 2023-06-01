from django.utils.translation import gettext_lazy as _

from axes.utils import reset
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK
from rest_framework.views import APIView

from .serializers import AxesResetSerializer


class AxesResetView(APIView):
    permission_classes = (
        IsAuthenticated,
        IsAdminUser,
    )

    @extend_schema(
        summary=_("Clear all access attempts."),
        description=_(
            "This is NOT meant for everyday usage but rather an emergency endpoint for solving a hot mess. TODO: implement a worker instead of blocking the app."
        ),
        responses={200: AxesResetSerializer},
        tags=["management"],
    )
    def post(self, request):
        count = reset()
        serializer = AxesResetSerializer({"count": count})
        return Response(data=serializer.data, status=HTTP_200_OK)
