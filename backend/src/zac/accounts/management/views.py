from django.utils.translation import gettext_lazy as _

from axes.utils import reset
from drf_spectacular.utils import extend_schema
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_204_NO_CONTENT
from rest_framework.views import APIView

from zac.accounts.api.permissions import HasTokenAuth
from zac.accounts.models import User

from ..authentication import ApplicationTokenAuthentication
from .commands.add_atomic_permissions import add_atomic_permissions
from .commands.add_blueprint_permissions_for_zaaktypen import (
    add_blueprint_permissions_for_zaaktypen_and_iots,
)
from .serializers import (
    AddBlueprintPermissionsSerializer,
    AxesResetSerializer,
    UserLogSerializer,
)
from .utils import send_access_log_email


class AxesResetView(APIView):
    authentication_classes = (TokenAuthentication,)
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


class ClearRecentlyViewedView(APIView):
    authentication_classes = (TokenAuthentication,)
    permission_classes = (
        IsAuthenticated,
        IsAdminUser,
    )

    @extend_schema(
        summary=_("Clear all recently viewed fields on all users."),
        description=_(
            "This is NOT meant for everyday usage but rather an emergency endpoint for solving a hot mess. TODO: implement a worker instead of blocking the app."
        ),
        request=None,
        responses={204: None},
        tags=["management"],
    )
    def post(self, request):
        users = User.objects.all()
        for user in users:
            user.recently_viewed = list()
        User.objects.bulk_update(users, ["recently_viewed"], batch_size=100)

        return Response(status=HTTP_204_NO_CONTENT)


class LoadBlueprintPermissionsView(APIView):
    authentication_classes = (TokenAuthentication,)
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
    authentication_classes = (TokenAuthentication,)
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


class UserLogView(APIView):
    authentication_classes = (
        ApplicationTokenAuthentication,
        TokenAuthentication,
    )
    permission_classes = (HasTokenAuth | IsAdminUser,)

    @extend_schema(
        summary=_("Email user logs"),
        description=_("Send daily user logs to recipient list."),
        request=UserLogSerializer,
        responses={
            "204": None,
        },
        tags=["management"],
    )
    def post(self, request):
        serializer = UserLogSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        send_access_log_email(**serializer.validated_data)
        return Response(status=HTTP_204_NO_CONTENT)
