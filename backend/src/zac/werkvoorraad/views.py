import logging
from typing import Dict, List

from django.utils.translation import gettext_lazy as _

from django_camunda.client import get_client
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import authentication, permissions, views
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from zgw_consumers.concurrent import parallel

from zac.activities.models import Activity
from zac.camunda.constants import AssigneeTypeChoices
from zac.camunda.data import Task
from zac.camunda.user_tasks.api import (
    get_camunda_user_task_count,
    get_camunda_user_tasks_for_assignee,
    get_camunda_user_tasks_for_user_groups,
    get_killable_camunda_tasks,
    get_zaak_urls_from_tasks,
)
from zac.contrib.objects.kownsl.data import ReviewRequest
from zac.contrib.objects.services import (
    count_review_requests_by_user,
    fetch_all_checklists_for_user_groups,
    fetch_all_unanswered_checklists_for_user,
    get_review_requests_paginated,
    get_reviews_for_requester,
)
from zac.core.api.pagination import ProxyPagination
from zac.core.api.permissions import CanHandleAccessRequests
from zac.elasticsearch.documents import ZaakDocument
from zac.elasticsearch.drf_api.filters import ESOrderingFilter
from zac.elasticsearch.drf_api.serializers import ZaakDocumentSerializer
from zac.elasticsearch.drf_api.utils import es_document_to_ordering_parameters
from zac.elasticsearch.searches import count_by_behandelaar, search_zaken

from .data import AccessRequestGroup, TaskAndCase
from .pagination import WorkstackPagination
from .serializers import (
    WorkStackAccessRequestsSerializer,
    WorkStackAdhocActivitiesSerializer,
    WorkStackChecklistAnswerSerializer,
    WorkStackReviewRequestSerializer,
    WorkStackSummarySerializer,
    WorkStackTaskSerializer,
)
from .utils import (
    count_access_requests,
    get_access_requests_groups,
    get_activity_groups,
    get_checklist_answers_groups,
)

logger = logging.getLogger(__name__)


@extend_schema(summary=_("List access requests for logged in user."))
class WorkStackAccessRequestsView(ListAPIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated & CanHandleAccessRequests,)
    serializer_class = WorkStackAccessRequestsSerializer
    filter_backends = ()
    pagination_class = WorkstackPagination

    def get_queryset(self):
        access_requests_groups = get_access_requests_groups(self.request)
        return [AccessRequestGroup(**group) for group in access_requests_groups]


@extend_schema(summary=_("List activities for logged in user."))
class WorkStackAdhocActivitiesView(ListAPIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = WorkStackAdhocActivitiesSerializer
    filter_backends = ()
    pagination_class = WorkstackPagination

    def get_activities(self) -> List[Dict]:
        return Activity.objects.as_werkvoorraad(user=self.request.user)

    def get_queryset(self):
        grouped_activities = self.get_activities()
        activity_groups = get_activity_groups(self.request, grouped_activities)
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
    request=None,
    responses={200: ZaakDocumentSerializer(many=True)},
)
class WorkStackAssigneeCasesView(ListAPIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = ZaakDocumentSerializer
    search_document = ZaakDocument
    pagination_class = WorkstackPagination
    ordering = ("-identificatie.keyword",)

    def get_queryset(self):
        if not hasattr(self, "_qs"):
            ordering = ESOrderingFilter().get_ordering(self.request, self)
            zaken = search_zaken(
                request=self.request,
                behandelaar=self.request.user.username,
                ordering=ordering,
            )
            self._qs = [zaak for zaak in zaken if not zaak.einddatum]
        return self._qs


@extend_schema(summary=_("List user tasks for logged in user."))
class WorkStackUserTasksView(ListAPIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = WorkStackTaskSerializer
    filter_backends = ()
    pagination_class = WorkstackPagination

    def get_client(self):
        if not hasattr(self, "_camunda_client"):
            self._camunda_client = get_client()
        return self._camunda_client

    def get_serializer_context(self) -> Dict:
        context = super().get_serializer_context()
        context.update({"killable_tasks": get_killable_camunda_tasks()})
        return context

    def get_camunda_tasks(self) -> List[Task]:
        tasks = get_camunda_user_tasks_for_assignee(
            [f"{AssigneeTypeChoices.user}:{self.request.user.username}"],
            client=self.get_client(),
        )
        return tasks

    def get_queryset(self):
        if not hasattr(self, "_qs"):
            tasks = {task.id: task for task in self.get_camunda_tasks()}
            if not tasks:
                return []

            task_ids_and_zaak_urls = get_zaak_urls_from_tasks(
                tasks.values(), client=self.get_client()
            )
            if not task_ids_and_zaak_urls:
                return []

            urls = list({url for url in task_ids_and_zaak_urls.values()})
            zaken = {
                zaak.url: zaak
                for zaak in search_zaken(
                    request=self.request, urls=urls, size=len(urls)
                )
            }
            task_zaken = dict()
            for task_id, zaak_url in task_ids_and_zaak_urls.items():
                if not (zaak := zaken.get(zaak_url)):
                    logger.warning(
                        "Couldn't find a ZAAK in Elasticsearch for task with id %s."
                        % task_id
                    )
                task_zaken[task_id] = zaak
            self._qs = sorted(
                [
                    TaskAndCase(task=tasks[task_id], zaak=task_zaken[task_id])
                    for task_id in task_ids_and_zaak_urls
                    if task_zaken[task_id]
                ],
                key=lambda tac: tac.zaak.identificatie,
                reverse=True,
            )

        return self._qs


@extend_schema(
    summary=_("List user tasks assigned to groups related to logged in user.")
)
class WorkStackGroupTasksView(WorkStackUserTasksView):
    def get_camunda_tasks(self) -> List[Task]:
        return get_camunda_user_tasks_for_user_groups(
            self.request.user, client=self.get_client()
        )


@extend_schema(summary=_("List checklist questions for logged in user."))
class WorkStackChecklistQuestionsView(views.APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = WorkStackChecklistAnswerSerializer
    filter_backends = ()

    def get_assigned_checklist_answers(self) -> List[Dict]:
        checklists = fetch_all_unanswered_checklists_for_user(self.request.user)
        answers_grouped_by_zaak_url = [
            {
                "zaak_url": checklist["zaak"],
                "checklist_answers": [
                    answer
                    for answer in checklist["answers"]
                    if self.request.user.username in answer.get("user_assignee", "")
                    and not answer["answer"]
                ],
            }
            for checklist in checklists
        ]
        return answers_grouped_by_zaak_url

    def get(self, request, *args, **kwargs):
        grouped_checklist_answers = self.get_assigned_checklist_answers()
        checklist_answers = get_checklist_answers_groups(
            request, grouped_checklist_answers
        )
        serializer = self.serializer_class(checklist_answers, many=True)
        return Response(serializer.data)


@extend_schema(
    summary=_("List checklist questions for groups of logged in user."),
)
class WorkStackGroupChecklistQuestionsView(WorkStackChecklistQuestionsView):
    def get_assigned_checklist_answers(self) -> List[Dict]:
        checklists = fetch_all_checklists_for_user_groups(self.request.user)
        groups = self.request.user.groups.all().values_list("name", flat=True)
        answers_grouped_by_zaak_url = [
            {
                "zaak_url": checklist["zaak"],
                "checklist_answers": [
                    answer
                    for answer in checklist["answers"]
                    if answer.get("group_assignee") in groups and not answer["answer"]
                ],
            }
            for checklist in checklists
        ]
        return answers_grouped_by_zaak_url


@extend_schema(
    summary=_("List review requests initiated by user."),
    parameters=[
        OpenApiParameter(
            name=ProxyPagination().page_size_query_param,
            default=ProxyPagination().page_size,
            type=OpenApiTypes.INT,
            description=_("Number of results to return per paginated response."),
            location=OpenApiParameter.QUERY,
        ),
        OpenApiParameter(
            name=ProxyPagination().page_query_param,
            type=OpenApiTypes.INT,
            default=1,
            description=_("Page number of paginated response."),
            location=OpenApiParameter.QUERY,
        ),
    ],
)
class WorkStackReviewRequestsView(views.APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = WorkStackReviewRequestSerializer
    filter_backends = ()
    pagination_class = ProxyPagination

    @property
    def paginator(self):
        if not hasattr(self, "_paginator"):
            self._paginator = self.pagination_class()
        return self._paginator

    def get_query_params(self) -> Dict:
        return {
            self.paginator.page_size_query_param: self.paginator.get_page_size(
                self.request
            ),
            self.paginator.page_query_param: self.request.query_params.get(
                self.paginator.page_query_param, 1
            ),
        }

    def resolve_zaken(
        self, review_requests: List[ReviewRequest]
    ) -> List[ReviewRequest]:
        urls = list({rr.zaak for rr in review_requests})
        zaken = {
            z.url: z
            for z in search_zaken(
                request=self.request, urls=urls, only_allowed=False, size=len(urls)
            )
        }
        for rr in review_requests:
            rr.zaak = zaken.get(rr.zaak, None)
        return review_requests

    def resolve_reviews(
        self, review_requests: List[ReviewRequest]
    ) -> List[ReviewRequest]:
        reviews = {}
        for review in get_reviews_for_requester(self.request.user):
            if review.review_request in reviews:
                reviews[review.review_request] += review.reviews
            else:
                reviews[review.review_request] = review.reviews

        for rr in review_requests:
            rr.reviews = sorted(
                reviews.get(str(rr.id), []), key=lambda x: x.created, reverse=True
            )
            rr.fetched_reviews = True
        return review_requests

    def get(self, request, *args, **kwargs):
        results, _query_params = get_review_requests_paginated(
            query_params=self.get_query_params(),
            requester=request.user,
        )
        review_requests = self.resolve_zaken(results["results"])
        review_requests = self.resolve_reviews(results["results"])

        results["results"] = self.serializer_class(
            instance=review_requests, many=True
        ).data
        return self.paginator.get_paginated_response(request, results)


class WorkStackSummaryView(views.APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = WorkStackSummarySerializer

    def post(self, request, *args, **kwargs):
        data = {}

        def _get_user_task_count():
            count = get_camunda_user_task_count(
                [f"{AssigneeTypeChoices.user}:{self.request.user}"]
            )
            return {"key": "user_tasks", "val": count}

        def _get_group_task_count():
            user_groups = list(
                self.request.user.groups.all().values_list("name", flat=True)
            )
            count = get_camunda_user_task_count(
                [f"{AssigneeTypeChoices.group}:{n}" for n in user_groups]
            )

            return {"key": "group_tasks", "val": count}

        def _count_zaken():
            count = count_by_behandelaar(request=request)
            return {"key": "zaken", "val": count}

        def _count_review_requests():
            count = count_review_requests_by_user(requester=request.user)
            return {"key": "reviews", "val": count or 0}

        def _count_user_activities():
            count = Activity.objects.filter(user_assignee=request.user).count()
            return {"key": "user_activities", "val": count}

        def _count_group_activities():
            user_groups = [
                n[0] for n in list(request.user.groups.all().values_list("id"))
            ]
            count = (
                Activity.objects.filter(group_assignee__in=user_groups).count()
                if user_groups
                else 0
            )
            return {"key": "group_activities", "val": count}

        def _count_access_requests():
            count = count_access_requests(request)
            return {"key": "access_requests", "val": count}

        fetch_these = [
            _get_user_task_count,
            _get_group_task_count,
            _count_zaken,
            _count_review_requests,
            _count_user_activities,
            _count_group_activities,
            _count_access_requests,
        ]
        with parallel(max_workers=10) as executor:
            data = list(executor.map(lambda fn: fn(), fetch_these))

        serializer = self.serializer_class({d["key"]: d["val"] for d in data})
        return Response(serializer.data)
