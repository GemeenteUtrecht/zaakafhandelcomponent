from django.core.management import call_command
from django.utils.translation import gettext_lazy as _

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_204_NO_CONTENT
from rest_framework.views import APIView


class IndexAllView(APIView):
    permission_classes = (
        IsAuthenticated,
        IsAdminUser,
    )

    @extend_schema(
        summary=_("Index everything in the elasticsearch index."),
        description=_(
            "This is NOT meant for everyday usage but rather an emergency endpoint for solving a hot mess. TODO: implement a worker instead of blocking the app."
        ),
        request=None,
        responses={204: None},
        tags=["management"],
    )
    def post(self, request):
        call_command("index_all")
        return Response(status=HTTP_204_NO_CONTENT)
