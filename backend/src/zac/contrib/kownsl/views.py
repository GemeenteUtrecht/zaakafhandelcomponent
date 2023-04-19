import logging

from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.utils.translation import gettext_lazy as _

from django_camunda.api import send_message
from django_camunda.client import get_client as get_camunda_client
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import authentication, exceptions, permissions, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from zgw_consumers.api_models.base import factory
from zgw_consumers.concurrent import parallel
from zgw_consumers.models import Service

from zac.camunda.api.utils import set_assignee_and_complete_task
from zac.camunda.constants import AssigneeTypeChoices
from zac.camunda.data import Task
from zac.core.api.permissions import CanReadZaken
from zac.core.api.views import GetZaakMixin
from zac.core.camunda.utils import resolve_assignee
from zac.core.services import get_document, get_zaak
from zac.notifications.views import BaseNotificationCallbackView

from .api import (
    get_client,
    get_review_request,
    get_review_requests,
    lock_review_request,
    retrieve_advices,
    retrieve_approvals,
)
from .data import ReviewRequest
from .permissions import (
    CanReadOrUpdateReviews,
    HasNotReviewed,
    IsReviewUser,
    ReviewIsUnlocked,
)
from .serializers import (
    KownslReviewRequestSerializer,
    UpdateZaakReviewRequestSerializer,
    ZaakRevReqDetailSerializer,
    ZaakRevReqSummarySerializer,
)
from .utils import remote_kownsl_create_schema

logger = logging.getLogger(__name__)


def _get_review_request_for_notification(data: dict) -> dict:
    resource_url = data["hoofd_object"]
    client = Service.get_client(resource_url)
    if client is None:
        raise RuntimeError(
            f"Could not build an appropriate client for the URL {resource_url}"
        )

    logger.debug("Retrieving review request %s", resource_url)
    review_request = client.retrieve("reviewrequest", url=resource_url)
    return review_request


class KownslNotificationCallbackView(BaseNotificationCallbackView):
    def handle_notification(self, data: dict):
        # just to make sure, shouldn't happen with our URL routing
        logger.debug("Kownsl notification: %r" % data)
        if not data["kanaal"] == "kownsl":
            return

        if data["actie"] == "reviewSubmitted":
            self._handle_review_submitted(data)

        if data["actie"] == "update":
            self._handle_review_updated(data)

    @staticmethod
    def _handle_review_updated(data: dict):
        review_request = _get_review_request_for_notification(data)
        # End the current process instance gracefully
        if data["kenmerken"].get("locked"):
            send_message(
                "cancel-process",
                [review_request["metadata"]["processInstanceId"]],
            )
        if data["kenmerken"].get("updated_users"):
            send_message(
                "change-process", [review_request["metadata"]["processInstanceId"]]
            )

    @staticmethod
    def _handle_review_submitted(data: dict):
        review_request = _get_review_request_for_notification(data)

        # look up and complete the user task in Camunda
        group_assignee = (
            f'{AssigneeTypeChoices.group}:{data["kenmerken"]["group"]}'
            if data["kenmerken"]["group"]
            else None
        )
        user_assignee = f'{AssigneeTypeChoices.user}:{data["kenmerken"]["author"]}'

        camunda_client = get_camunda_client()

        params = {
            "processInstanceId": review_request["metadata"]["processInstanceId"],
            "taskDefinitionKey": review_request["metadata"]["taskDefinitionId"],
            "assignee": group_assignee or user_assignee,
        }
        logger.debug("Finding user tasks matching %r", params)
        tasks = camunda_client.get("task", params)

        if not tasks:
            logger.info(
                "No user tasks found - possibly they were already marked completed. "
            )
            return

        if len(tasks) > 1:
            logger.warning(
                "Multiple user tasks with the same assignee and definition found in a single process instance!",
                extra={"tasks": tasks, "params": params},
            )

        tasks = factory(Task, tasks)
        for task in tasks:
            set_assignee_and_complete_task(
                task, user_assignee, variables={"author": user_assignee}
            )


class BaseRequestView(APIView):
    """
    This view allows a user to get relevant review request data from the kownsl API to be able to form an advice,
    and post their advice/approval to the kownsl component.

    * Requires that the requesting user is authenticated and found in review_request.user_deadlines
    """

    permission_classes = (
        IsAuthenticated,
        IsReviewUser,
        HasNotReviewed,
        ReviewIsUnlocked,
    )
    _operation_id = NotImplemented
    serializer_class = KownslReviewRequestSerializer

    def get_object(self):
        client = get_client(self.request.user)
        review_request = client.retrieve(
            "review_requests", uuid=self.kwargs["request_uuid"]
        )
        rr = factory(ReviewRequest, review_request)
        # underscorize in factory is messing with the format of the keys in the user_deadlines dictionary
        rr.user_deadlines = review_request["userDeadlines"]
        self.check_object_permissions(self.request, rr)
        return review_request

    def get(self, request, request_uuid):
        if not (request.query_params.get("assignee")):
            raise exceptions.ValidationError("'assignee' query parameter is required.")

        review_request = self.get_object()
        zaak_url = review_request["forZaak"]
        review_request["zaak"] = get_zaak(zaak_url=zaak_url)
        serializer = self.serializer_class(
            instance=review_request,
            context={"request": request, "view": self},
        )
        return Response(serializer.data)

    def post(self, request, request_uuid):
        if not (assignee := request.query_params.get("assignee")):
            raise exceptions.ValidationError("'assignee' query parameter is required.")
        data = {**request.data}
        assignee = resolve_assignee(assignee)
        if isinstance(assignee, Group):
            data["group"] = f"{assignee}"

        # Check if user is allowed to get and post based on source review request user_deadlines value.
        self.get_object()
        client = get_client(request.user)
        response = client.create(
            self._operation_resource,
            data=data,
            request__uuid=request_uuid,
        )
        return Response(response, status=status.HTTP_201_CREATED)


ASSIGNEE_PARAMETER = OpenApiParameter(
    name="assignee",
    required=True,
    type=OpenApiTypes.STR,
    description=_("Assignee of the user task in camunda."),
    location=OpenApiParameter.QUERY,
)


@extend_schema_view(
    get=extend_schema(
        summary=_("Retrieve advice review request."),
        parameters=[ASSIGNEE_PARAMETER],
    ),
    post=remote_kownsl_create_schema(
        "/api/v1/review-requests/{request__uuid}/advices",
        summary=_("Register advice for review request."),
        parameters=[ASSIGNEE_PARAMETER],
    ),
)
class AdviceRequestView(BaseRequestView):
    _operation_resource = "review_requests_advices"


@extend_schema_view(
    get=extend_schema(
        summary=_("Retrieve approval review request."),
        parameters=[ASSIGNEE_PARAMETER],
    ),
    post=remote_kownsl_create_schema(
        "/api/v1/review-requests/{request__uuid}/approvals",
        summary=_("Register approval for review request."),
        parameters=[ASSIGNEE_PARAMETER],
    ),
)
class ApprovalRequestView(BaseRequestView):
    _operation_resource = "review_requests_approvals"


class ZaakReviewRequestSummaryView(GetZaakMixin, APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (
        permissions.IsAuthenticated,
        CanReadZaken,
    )

    def get_serializer(self, **kwargs):
        return ZaakRevReqSummarySerializer(many=True, **kwargs)

    @extend_schema(summary=_("List review requests summary for a ZAAK."))
    def get(self, request, *args, **kwargs):
        zaak = self.get_object()
        review_requests = get_review_requests(zaak)
        serializer = self.get_serializer(
            instance=review_requests, context={"request": request}
        )
        return Response(serializer.data)


class ZaakReviewRequestDetailView(APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (
        permissions.IsAuthenticated,
        CanReadOrUpdateReviews,
        ReviewIsUnlocked,
    )

    def get_serializer(self, **kwargs):
        mapping = {
            "GET": ZaakRevReqDetailSerializer,
            "PATCH": UpdateZaakReviewRequestSerializer,
        }
        return mapping[self.request.method](**kwargs)

    def get_object(self) -> ReviewRequest:
        review_request = get_review_request(self.kwargs["request_uuid"])
        self.check_object_permissions(self.request, review_request)
        return review_request

    def get_review_request_metadata(self, review_request: ReviewRequest):
        with parallel() as executor:
            review_request.advices = []
            if review_request.num_advices:
                _advices = executor.submit(retrieve_advices, review_request)
                review_request.advices = _advices.result()

            review_request.approvals = []
            if review_request.num_approvals:
                _approvals = executor.submit(retrieve_approvals, review_request)
                review_request.approvals = _approvals.result()

        documents = set()
        for advice in review_request.advices:
            for document in advice.documents:
                documents.add(document.document)

        with parallel() as executor:
            _documents = executor.map(get_document, documents)

        documents = {doc.url: doc for doc in _documents}

        advices = []
        for advice in review_request.advices:
            advice_documents = []
            for advice_document in advice.documents:
                advice_document.document = documents[advice_document.document]
                advice_documents.append(advice_document)

            advice.documents = advice_documents
            advices.append(advice)

        review_request.advices = advices
        return review_request

    @extend_schema(
        summary=_("Retrieve review request."),
        responses={
            "200": ZaakRevReqDetailSerializer,
        },
    )
    def get(self, request, request_uuid, *args, **kwargs):
        review_request = self.get_object()
        review_request = self.get_review_request_metadata(review_request)
        serializer = self.get_serializer(instance=review_request)
        return Response(serializer.data)

    @extend_schema(
        summary=_("Partially update the review request."),
        responses={
            "200": ZaakRevReqDetailSerializer,
        },
    )
    def patch(self, request, request_uuid, *args, **kwargs):
        review_request = self.get_object()
        self.check_object_permissions(self.request, review_request)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if lock_reason := serializer.validated_data.get("lock_reason"):
            review_request = lock_review_request(request_uuid, lock_reason=lock_reason)

        elif serializer.validated_data.get("update_users"):
            send_message(
                "change-process", [review_request.metadata["process_instance_id"]]
            )

        review_request = self.get_review_request_metadata(review_request)
        response_serializer = ZaakRevReqDetailSerializer(instance=review_request)
        return Response(response_serializer.data)


class ZaakReviewRequestReminderView(APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (
        permissions.IsAuthenticated,
        CanReadOrUpdateReviews,
        ReviewIsUnlocked,
    )

    def get_object(self) -> ReviewRequest:
        review_request = get_review_request(self.kwargs["request_uuid"])

        # Check if review request is locked and if user is a requester or has zaak update rights
        self.check_object_permissions(self.request, review_request)
        return review_request

    @extend_schema(
        summary=_("Send a reminder to reviewees."),
        request=None,
        responses={
            204: None,
        },
    )
    def post(self, request, request_uuid, *args, **kwargs):
        review_request = self.get_object()
        send_message(
            "_kownsl_reminder",
            [review_request.metadata["process_instance_id"]],
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
