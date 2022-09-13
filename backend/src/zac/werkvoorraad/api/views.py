import logging
from typing import Dict, List

from django.utils.translation import gettext as _

from drf_spectacular.utils import extend_schema
from rest_framework import authentication, permissions, views
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from zgw_consumers.api_models.base import factory
from zgw_consumers.concurrent import parallel

from zac.activities.models import Activity
from zac.api.context import get_zaak_url_from_context
from zac.camunda.data import Task
from zac.camunda.user_tasks.api import get_killable_camunda_tasks
from zac.core.api.mixins import ListMixin
from zac.core.api.permissions import CanHandleAccessRequests
from zac.elasticsearch.documents import ZaakDocument
from zac.elasticsearch.drf_api.filters import ESOrderingFilter
from zac.elasticsearch.drf_api.serializers import ZaakDocumentSerializer
from zac.elasticsearch.drf_api.utils import es_document_to_ordering_parameters
from zac.elasticsearch.searches import search
from zac.objects.services import (
    fetch_all_checklists_for_user,
    fetch_all_checklists_for_user_groups,
)

from .data import AccessRequestGroup, TaskAndCase
from .serializers import (
    WorkStackAccessRequestsSerializer,
    WorkStackAdhocActivitiesSerializer,
    WorkStackChecklistAnswerSerializer,
    WorkStackTaskSerializer,
)
from .utils import (
    get_access_requests_groups,
    get_activity_groups,
    get_camunda_group_tasks,
    get_camunda_user_tasks,
    get_checklist_answers_groups,
)

logger = logging.getLogger(__name__)


@extend_schema(summary=_("List access requests for logged in user."))
class WorkStackAccessRequestsView(ListAPIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated & CanHandleAccessRequests,)
    serializer_class = WorkStackAccessRequestsSerializer
    filter_backends = ()

    def get_queryset(self):
        access_requests_groups = get_access_requests_groups(self.request.user)
        return [AccessRequestGroup(**group) for group in access_requests_groups]


@extend_schema(summary=_("List activities for logged in user."))
class WorkStackAdhocActivitiesView(ListAPIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = WorkStackAdhocActivitiesSerializer
    filter_backends = ()

    def get_activities(self) -> List[Dict]:
        return Activity.objects.as_werkvoorraad(user=self.request.user)

    def get_queryset(self):
        grouped_activities = self.get_activities()
        activity_groups = get_activity_groups(self.request.user, grouped_activities)
        return activity_groups


@extend_schema(
    summary=_("List activities for groups of logged in user."),
)
class WorkStackGroupAdhocActivitiesView(WorkStackAdhocActivitiesView):
    def get_activities(self) -> List[Dict]:
        return Activity.objects.as_werkvoorraad(groups=self.request.user.groups.all())


@extend_schema(
    summary=_("List active ZAAKen for logged in user."),
    parameters=[es_document_to_ordering_parameters(ZaakDocument)],
)
class WorkStackAssigneeCasesView(ListMixin, views.APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ZaakDocumentSerializer
    search_document = ZaakDocument
    ordering = ("-deadline",)

    def get_objects(self):
        ordering = ESOrderingFilter().get_ordering(self.request, self)
        zaken = search(
            user=self.request.user,
            behandelaar=self.request.user.username,
            ordering=ordering,
        )
        return [zaak for zaak in zaken if not zaak.einddatum]


@extend_schema(summary=_("List user tasks for logged in user."))
class WorkStackUserTasksView(ListAPIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = WorkStackTaskSerializer
    filter_backends = ()

    def get_serializer_context(self) -> Dict:
        context = super().get_serializer_context()
        context.update({"killable_tasks": get_killable_camunda_tasks()})
        return context

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
        task_zaken = {}
        for task_id, zaak_url in task_ids_and_zaak_urls:
            if not (zaak := zaken.get(zaak_url)):
                logger.warning(
                    "Couldn't find a ZAAK in Elasticsearch for task with id %s."
                    % task_id
                )

            task_zaken[task_id] = zaak

        return [
            TaskAndCase(task=task, zaak=task_zaken[task.id])
            for task in tasks
            if task_zaken[task.id]
        ]


@extend_schema(
    summary=_("List user tasks assigned to groups related to logged in user.")
)
class WorkStackGroupTasksView(WorkStackUserTasksView):
    def get_camunda_tasks(self) -> List[Task]:
        return get_camunda_group_tasks(self.request.user)


@extend_schema(summary=_("List checklist questions for logged in user."))
class WorkStackChecklistQuestionsView(views.APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = WorkStackChecklistAnswerSerializer
    filter_backends = ()

    def get_assigned_checklist_answers(self) -> List[Dict]:
        checklists = fetch_all_checklists_for_user(self.request.user)
        answers_grouped_by_zaak = []
        for checklist in checklists:
            answer_group = {"zaak_url": checklist["zaak"], "checklist_answers": []}
            for answer in checklist["answers"]:
                if answer.get("user_assignee") == self.request.user.username:
                    answer_group["checklist_answers"].append(answer)

            answers_grouped_by_zaak.append(answer_group)

        return answers_grouped_by_zaak

    def get(self, request, *args, **kwargs):
        grouped_checklist_answers = self.get_assigned_checklist_answers()
        checklist_answers = get_checklist_answers_groups(
            self.request.user, grouped_checklist_answers
        )
        serializer = self.serializer_class(checklist_answers, many=True)
        return Response(serializer.data)


@extend_schema(
    summary=_("List checklist questions for groups of logged in user."),
)
class WorkStackGroupChecklistQuestionsView(WorkStackChecklistQuestionsView):
    def get_assigned_checklist_answers(self) -> List[Dict]:
        checklists = fetch_all_checklists_for_user_groups(self.request.user)
        answers_grouped_by_zaak = []
        groups = self.request.user.groups.all().values_list("name", flat=True)
        for checklist in checklists:
            answer_group = {"zaak_url": checklist["zaak"], "checklist_answers": []}
            for answer in checklist["answers"]:
                if answer.get("group_assignee") in groups:
                    answer_group["checklist_answers"].append(answer)

            answers_grouped_by_zaak.append(answer_group)

        return answers_grouped_by_zaak
