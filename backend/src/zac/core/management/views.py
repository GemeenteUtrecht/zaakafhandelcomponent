from django.utils.translation import gettext_lazy as _

from drf_spectacular.utils import extend_schema
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK
from rest_framework.views import APIView

from .serializers import CacheResetSerializer


class CacheResetView(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (
        IsAuthenticated,
        IsAdminUser,
    )
    serializer_class = CacheResetSerializer

    @extend_schema(
        summary=_("Clear all cache key-value pairs."),
        description=_(
            "This is NOT meant for everyday usage but rather an emergency endpoint for solving a hot mess. TODO: implement a worker instead of blocking the app."
        ),
        tags=["management"],
    )
    def post(self, request):
        serializer = CacheResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        count = serializer.perform()
        return Response(data=serializer.data, status=HTTP_200_OK)
