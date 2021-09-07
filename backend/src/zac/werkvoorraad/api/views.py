from zac.camunda.data import Task
from typing import List

from django.utils.translation import gettext as _

from drf_spectacular.utils import extend_schema
from rest_framework import authentication, permissions
from rest_framework.generics import ListAPIView
from zds_client import ClientError
from zgw_consumers.concurrent import parallel

from zac.activities.models import Activity
from zac.api.context import get_zaak_context
from zac.core.api.permissions import CanHandleAccessRequests
from zac.core.api.serializers import ZaakDetailSerializer
from zac.core.services import get_zaak
from zac.elasticsearch.documents import ZaakDocument
from zac.elasticsearch.drf_api.filters import ESOrderingFilter
from zac.elasticsearch.drf_api.utils import es_document_to_ordering_parameters

from .data import AccessRequestGroup, ActivityGroup, TaskAndCase
from .serializers import (
    WorkStackAccessRequestsSerializer,
    WorkStackAdhocActivitiesSerializer,
    WorkStackTaskSerializer,
)
from .utils import (
    get_access_requests_groups,
    get_behandelaar_zaken_unfinished,
    get_camunda_user_tasks,
    get_camunda_group_tasks,
)


@extend_schema(summary=_("List access requests"))
class WorkStackAccessRequestsView(ListAPIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated & CanHandleAccessRequests,)
    serializer_class = WorkStackAccessRequestsSerializer
    filter_backends = ()

    def get_queryset(self):
        access_requests_groups = get_access_requests_groups(self.request.user)
        return [AccessRequestGroup(**group) for group in access_requests_groups]


@extend_schema(summary=_("List adhoc activities"))
class WorkStackAdhocActivitiesView(ListAPIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = WorkStackAdhocActivitiesSerializer
    filter_backends = ()

    def get_queryset(self):
        activity_groups = Activity.objects.as_werkvoorraad(user=self.request.user)

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
        return groups


@extend_schema(
    summary=_("List active cases"),
    parameters=[es_document_to_ordering_parameters(ZaakDocument)],
)
class WorkStackAssigneeCasesView(ListAPIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ZaakDetailSerializer
    search_document = ZaakDocument
    ordering = ("-deadline",)

    def get_queryset(self):
        ordering = ESOrderingFilter().get_ordering(self.request, self)
        unfinished_zaken = get_behandelaar_zaken_unfinished(
            self.request.user,
            ordering=ordering,
        )
        # TODO: Add support for resultaat in ES
        for zaak in unfinished_zaken:
            zaak.resultaat = None
        return unfinished_zaken


@extend_schema(summary=_("List user tasks"))
class WorkStackUserTasksView(ListAPIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = WorkStackTaskSerializer
    filter_backends = ()

    def get_camunda_tasks(self) -> List[Task]:
        return get_camunda_user_tasks(self.request.user)

    def get_queryset(self):
        tasks = self.get_camunda_tasks()
        with parallel() as executor:
            zaken_context = executor.map(get_zaak_context, tasks)

        return [
            TaskAndCase(task=task, zaak=zaak_context.zaak)
            for task, zaak_context in zip(tasks, zaken_context)
        ]


@extend_schema(summary=_("List user tasks assigned to groups related to user"))
class WorkStackGroupsTasksView(WorkStackUserTasksView):
    def get_camunda_tasks(self) -> List[Task]:
        return get_camunda_group_tasks(self.request.user)
