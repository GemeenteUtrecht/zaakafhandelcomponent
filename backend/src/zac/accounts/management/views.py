from django.utils.translation import gettext_lazy as _

from axes.utils import reset
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_204_NO_CONTENT
from rest_framework.views import APIView

from .commands.add_atomic_permissions import add_atomic_permissions
from .commands.add_blueprint_permissions_for_zaaktypen import (
    add_blueprint_permissions_for_zaaktypen_and_iots,
)
from .serializers import AddBlueprintPermissionsSerializer, AxesResetSerializer


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
        request=None,
        responses={200: AxesResetSerializer},
        tags=["management"],
    )
    def post(self, request):
        count = reset()
        serializer = AxesResetSerializer({"count": count})
        return Response(data=serializer.data, status=HTTP_200_OK)


class LoadBlueprintPermissionsView(APIView):
    permission_classes = (
        IsAuthenticated,
        IsAdminUser,
    )

    @extend_schema(
        summary=_("Load all blueprint permissions."),
        description=_(
            "This is NOT meant for everyday usage but rather an emergency endpoint for solving a hot mess. TODO: implement a worker instead of blocking the app."
        ),
        request=None,
        responses={200: AddBlueprintPermissionsSerializer},
        tags=["management"],
    )
    def post(self, request):
        count = add_blueprint_permissions_for_zaaktypen_and_iots()
        serializer = AddBlueprintPermissionsSerializer({"count": count})
        return Response(data=serializer.data, status=HTTP_200_OK)


class AddAtomicPermissionsView(APIView):
    permission_classes = (
        IsAuthenticated,
        IsAdminUser,
    )

    @extend_schema(
        summary=_("Add all atomic permissions for behandelaren and advisors."),
        description=_(
            "This is NOT meant for everyday usage but rather an emergency endpoint for solving a hot mess. TODO: implement a worker instead of blocking the app."
        ),
        request=None,
        responses={204: None},
        tags=["management"],
    )
    def post(self, request):
        add_atomic_permissions()
        return Response(status=HTTP_204_NO_CONTENT)
