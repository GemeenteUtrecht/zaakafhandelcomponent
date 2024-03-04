from django.utils.translation import gettext_lazy as _

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK
from rest_framework.views import APIView

from .commands.unlock_checklists import unlock_command
from .serializers import UnlockCountSerializer


class UnlockChecklistsView(APIView):
    permission_classes = (
        IsAuthenticated,
        IsAdminUser,
    )

    @extend_schema(
        summary=_("Unlock all locked checklists."),
        description=_(
            "This is NOT meant for everyday usage but rather an emergency endpoint for solving a hot mess."
        ),
        request=None,
        responses={200: UnlockCountSerializer},
        tags=["management"],
    )
    def post(self, request):
        count = unlock_command()
        serializer = UnlockCountSerializer({"count": count})
        return Response(data=serializer.data, status=HTTP_200_OK)
