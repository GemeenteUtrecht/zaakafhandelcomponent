from django.utils.translation import gettext as _

from drf_spectacular.utils import extend_schema
from rest_framework import authentication, permissions, views
from rest_framework.generics import ListAPIView
from rest_framework.request import Request
from rest_framework.response import Response
from zds_client import ClientError
from zgw_consumers.concurrent import parallel

from zac.activities.models import Activity
from zac.camunda.api.serializers import TaskSerializer
from zac.core.api.permissions import CanHandleAccessRequests
from zac.core.api.serializers import ZaakDetailSerializer
from zac.core.services import get_zaak

from ..views import (
    get_access_requests_groups,
    get_behandelaar_zaken_unfinished,
    get_camunda_user_tasks,
)
from .data import AccessRequestGroup, ActivityGroup
from .serializers import (
    WorkStackAccessRequestsSerializer,
    WorkStackAdhocActivitiesSerializer,
)


@extend_schema(summary=_("List access requests"))
class WorkStackAccessRequestsView(ListAPIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated & CanHandleAccessRequests,)
    serializer_class = WorkStackAccessRequestsSerializer

    def get_queryset(self):
        access_requests_groups = get_access_requests_groups(self.request.user)
        return [AccessRequestGroup(**group) for group in access_requests_groups]


class WorkStackAdhocActivitiesView(views.APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    def get_serializer(self, **kwargs):
        return WorkStackAdhocActivitiesSerializer(many=True, **kwargs)

    @extend_schema(
        summary=_("List adhoc activities"),
    )
    def get(self, request: Request) -> Response:
        activity_groups = Activity.objects.as_werkvoorraad(user=request.user)

        def set_zaak(group):
            try:
                group["zaak"] = get_zaak(zaak_url=group["zaak_url"])
            except ClientError as exc:
                if exc.args[0]["status"] == 404:  # zaak deleted / no longer exists
                    return
                raise

        with parallel() as executor:
            for activity_group in activity_groups:
                executor.submit(set_zaak, activity_group)

        groups = [
            ActivityGroup(**group) for group in activity_groups if "zaak" in group
        ]
        serializer = self.get_serializer(instance=groups, context={"request": request})
        return Response(serializer.data)


class WorkStackAssigneeCasesView(views.APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(
        summary=_("List active cases"),
    )
    def get_serializer(self, **kwargs):
        return ZaakDetailSerializer(many=True, **kwargs)

    def get(self, request: Request) -> Response:
        zaken = get_behandelaar_zaken_unfinished(request.user)
        serializer = self.get_serializer(instance=zaken)
        return Response(serializer.data)


class WorkStackUserTasksView(views.APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)

    @extend_schema(
        summary=_("List user tasks"),
    )
    def get_serializer(self, **kwargs):
        return TaskSerializer(many=True, **kwargs)

    def get(self, request: Request) -> Response:
        user_tasks = get_camunda_user_tasks(request.user)
        serializer = self.get_serializer(instance=user_tasks)
        return Response(serializer.data)
