from itertools import groupby
from typing import List

from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext as _
from django.views.generic import TemplateView

from django_camunda.camunda_models import Task, factory
from django_camunda.client import get_client
from rest_framework import authentication, permissions, views as drf_views
from rest_framework.request import Request
from rest_framework.response import Response
from zds_client import ClientError
from zgw_consumers.concurrent import parallel

from zac.accounts.models import AccessRequest, User
from zac.activities.models import Activity
from zac.camunda.api.serializers import TaskSerializer
from zac.core.api.permissions import CanHandleAccessRequests
from zac.core.permissions import zaken_handle_access
from zac.core.services import get_behandelaar_zaken, get_zaak
from zgw.models.zrc import Zaak

from .data import AccessRequestGroup, ActivityGroup
from .serializers import (
    WorkStackAccessRequestsSerializer,
    WorkStackAdhocActivitiesSerializer,
    WorkStackAssigneeCasesSerializer,
    WorkStackUserTaskSerializer,
)


def get_behandelaar_zaken_unfinished(user: User) -> List[Zaak]:
    """
    Retrieve the un-finished zaken where `user` is a medewerker in the role of behandelaar.
    """
    zaken = get_behandelaar_zaken(user)
    unfinished_zaken = [zaak for zaak in zaken if not zaak.einddatum]
    return sorted(unfinished_zaken, key=lambda zaak: zaak.deadline)


def get_camunda_user_tasks(user: User):
    client = get_client()
    tasks = client.get("task", {"assignee": user.username})

    tasks = factory(Task, tasks)
    for task in tasks:
        task.assignee = user

    return tasks


def get_access_requests_groups(user: User):
    # if user doesn't have a permission to handle access requests - don't show them
    if not user.has_perm(zaken_handle_access.name):
        return []

    behandelaar_zaken = {zaak.url: zaak for zaak in get_behandelaar_zaken(user)}
    access_requests = AccessRequest.objects.filter(
        result="", zaak__in=list(behandelaar_zaken.keys())
    ).order_by("zaak", "requester__username")

    requested_zaken = []
    for zaak_url, group in groupby(access_requests, key=lambda a: a.zaak):
        requested_zaken.append(
            {
                "zaak_url": zaak_url,
                "requesters": list(group),
                "zaak": behandelaar_zaken[zaak_url],
            }
        )
    return requested_zaken


class WorkStackAccessRequestsView(drf_views.APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated & CanHandleAccessRequests,)
    schema_summary = _("List access requests")

    def get_serializer(self, **kwargs):
        return WorkStackAccessRequestsSerializer(many=True, **kwargs)

    def get(self, request: Request) -> Response:
        access_requests_groups = get_access_requests_groups(request.user)
        access_requests_groups = [
            AccessRequestGroup(**group) for group in access_requests_groups
        ]
        serializer = self.get_serializer(instance=access_requests_groups)
        return Response(serializer.data)


class WorkStackAdhocActivitiesView(drf_views.APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    schema_summary = _("List adhoc activities")

    def get_serializer(self, **kwargs):
        return WorkStackAdhocActivitiesSerializer(many=True, **kwargs)

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


class WorkStackAssigneeCasesView(drf_views.APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    schema_summary = _("List active cases")

    def get_serializer(self, **kwargs):
        return WorkStackAssigneeCasesSerializer(many=True, **kwargs)

    def get(self, request: Request) -> Response:
        zaken = get_behandelaar_zaken_unfinished(request.user)
        serializer = self.get_serializer(instance=zaken)
        return Response(serializer.data)


class WorkStackUserTasksView(drf_views.APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    schema_summary = _("List user tasks")

    def get_serializer(self, **kwargs):
        return WorkStackUserTaskSerializer(many=True, **kwargs)

    def get(self, request: Request) -> Response:
        user_tasks = get_camunda_user_tasks(request.user)
        serializer = self.get_serializer(instance=user_tasks)
        return Response(serializer.data)


class SummaryView(LoginRequiredMixin, TemplateView):
    template_name = "index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # TODO: Camunda user tasks

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

        context.update(
            {
                "zaken": get_behandelaar_zaken_unfinished(self.request.user),
                "adhoc_activities": [
                    group for group in activity_groups if "zaak" in group
                ],
                "user_tasks": get_camunda_user_tasks(self.request.user),
                "access_requests": get_access_requests_groups(self.request.user),
            }
        )

        return context
