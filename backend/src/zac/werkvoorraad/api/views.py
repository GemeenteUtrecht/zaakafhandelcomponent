from typing import List

from django.contrib.auth.models import Group
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as _

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import authentication, permissions
from rest_framework.generics import ListAPIView
from zgw_consumers.concurrent import parallel

from zac.api.context import get_zaak_url_from_context
from zac.camunda.data import Task
from zac.core.api.permissions import CanHandleAccessRequests
from zac.elasticsearch.documents import ZaakDocument
from zac.elasticsearch.drf_api.filters import ESOrderingFilter
from zac.elasticsearch.drf_api.serializers import ZaakDocumentSerializer
from zac.elasticsearch.drf_api.utils import es_document_to_ordering_parameters
from zac.elasticsearch.searches import search

from .data import AccessRequestGroup, ActivityGroup, TaskAndCase
from .serializers import (
    WorkStackAccessRequestsSerializer,
    WorkStackAdhocActivitiesSerializer,
    WorkStackTaskSerializer,
)
from .utils import (
    get_access_requests_groups,
    get_activity_groups,
    get_camunda_group_tasks,
    get_camunda_user_tasks,
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


@extend_schema(summary=_("List adhoc activities by user"))
class WorkStackAdhocActivitiesView(ListAPIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = WorkStackAdhocActivitiesSerializer
    filter_backends = ()

    def get_queryset(self):
        activity_groups = get_activity_groups(self.request.user)
        return [ActivityGroup(**group) for group in activity_groups if "zaak" in group]


@extend_schema(
    summary=_("List adhoc activities by the group of a user"),
    parameters=[
        OpenApiParameter(
            name="group_assignee",
            required=True,
            type=OpenApiTypes.STR,
            description=_("The name of the group assigned to the activity."),
            location=OpenApiParameter.QUERY,
        )
    ],
)
class WorkStackGroupAdhocActivitiesView(WorkStackAdhocActivitiesView):
    def get_activities(self) -> List[dict]:
        group_assignee = self.request.query_params.get("group_assignee")
        if not group_assignee:
            return []

        group = get_object_or_404(Group, name__iexact=group_assignee)
        if group in self.request.user.groups.all():
            return Activity.objects.as_werkvoorraad(group=group)

        return []


@extend_schema(
    summary=_("List active cases"),
    parameters=[es_document_to_ordering_parameters(ZaakDocument)],
)
class WorkStackAssigneeCasesView(ListAPIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ZaakDocumentSerializer
    search_document = ZaakDocument
    ordering = ("-deadline",)

    def get_queryset(self):
        ordering = ESOrderingFilter().get_ordering(self.request, self)
        zaken = search(
            user=self.request.user,
            behandelaar=self.request.user.username,
            ordering=ordering,
        )
        unfinished_zaken = [zaak for zaak in zaken if not zaak.einddatum]
        return unfinished_zaken


@extend_schema(summary=_("List user tasks"))
class WorkStackUserTasksView(ListAPIView):
    # authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = WorkStackTaskSerializer
    filter_backends = ()

    def get_camunda_tasks(self) -> List[Task]:
        return get_camunda_user_tasks(self.request.user)

    def get_queryset(self):
        tasks = self.get_camunda_tasks()
        with parallel() as executor:
            task_ids_and_zaak_urls = list(
                executor.map(get_zaak_url_from_context, tasks)
            )

        zaken = {
            zaak.url: zaak
            for zaak in search(
                user=self.request.user,
                urls=list({tzu[1] for tzu in task_ids_and_zaak_urls}),
            )
        }
        task_zaken = {tzu[0]: zaken.get(tzu[1]) for tzu in task_ids_and_zaak_urls}

        return [TaskAndCase(task=task, zaak=task_zaken[task.id]) for task in tasks]


@extend_schema(summary=_("List user tasks assigned to groups related to user"))
class WorkStackGroupTasksView(WorkStackUserTasksView):
    def get_camunda_tasks(self) -> List[Task]:
        return get_camunda_group_tasks(self.request.user)
