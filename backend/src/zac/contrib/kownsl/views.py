import logging
from copy import copy

from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.utils.translation import gettext_lazy as _

from django_camunda.api import complete_task
from django_camunda.client import get_client as get_camunda_client
from drf_spectacular.utils import extend_schema_view
from rest_framework import authentication, permissions, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from zds_client.client import get_operation_url
from zgw_consumers.concurrent import parallel
from zgw_consumers.models import Service

from zac.core.api.permissions import CanReadZaken
from zac.core.api.views import GetZaakMixin
from zac.core.services import get_zaak
from zac.notifications.views import BaseNotificationCallbackView

from .api import (
    get_client,
    get_review_request,
    get_review_requests,
    retrieve_advices,
    retrieve_approvals,
)
from .permissions import IsReviewUser
from .serializers import ZaakRevReqDetailSerializer, ZaakRevReqSummarySerializer
from .utils import remote_kownsl_create_schema, remote_kownsl_get_schema

logger = logging.getLogger(__name__)


class KownslNotificationCallbackView(BaseNotificationCallbackView):
    def handle_notification(self, data: dict):
        # just to make sure, shouldn't happen with our URL routing
        if not data["kanaal"] == "kownsl":
            return

        if data["actie"] == "reviewSubmitted":
            self._handle_review_submitted(data)

    @staticmethod
    def _handle_review_submitted(data: dict):
        client = Service.get_client(data["hoofd_object"])

        logger.debug("Retrieving review request %s", data["hoofd_object"])
        review_request = client.retrieve("reviewrequest", url=data["hoofd_object"])

        # look up and complete the user task in Camunda
        assignee = data["kenmerken"]["author"]
        camunda_client = get_camunda_client()

        params = {
            "processInstanceId": review_request["metadata"]["processInstanceId"],
            "taskDefinitionKey": review_request["metadata"]["taskDefinitionId"],
            "assignee": assignee,
        }
        logger.debug("Finding user tasks matching %r", params)
        tasks = camunda_client.get("task", params)

        if not tasks:
            logger.info(
                "No user tasks found - possibly they were already marked completed."
            )
            return

        if len(tasks) > 1:
            logger.warning(
                "Multiple user tasks with the same assignee and definition found in a single process instance!",
                extra={"tasks": tasks, "params": params},
            )

        for task in tasks:
            complete_task(task["id"], variables={})


class BaseRequestView(APIView):
    """
    This view allows a user to get relevant review request data from the kownsl API to be able to form an advice,
    and post their advice/approval to the kownsl component.

    * Requires that the requesting user is authenticated and found in review_request.user_deadlines
    """

    permission_classes = (IsAuthenticated & IsReviewUser,)
    _operation_id = NotImplemented
    serializer_class = None  # this only serves to shut up drf-spectacular errors

    def get_object(self):
        client = get_client(self.request.user)
        operation_id = "reviewrequest_retrieve"
        url = get_operation_url(
            client.schema,
            operation_id,
            uuid=self.kwargs["request_uuid"],
        )
        review_request = client.request(url, operation_id)
        self.check_object_permissions(self.request, review_request)
        return review_request

    @remote_kownsl_get_schema("/api/v1/review-requests/{uuid}")
    def get(self, request, request_uuid):
        review_request = self.get_object()
        review_users = [
            review["author"]["username"] for review in review_request["reviews"]
        ]
        headers = {
            "X-Kownsl-Submitted": "true"
            if request.user.username in review_users
            else "false"
        }
        return Response(review_request, headers=headers)

    def post(self, request, request_uuid):
        # Check if user is allowed to get and post based on source review request user_deadlines value.
        self.get_object()

        client = get_client(request.user)
        operation_id = self._operation_id
        url = get_operation_url(
            client.schema,
            operation_id,
            parent_lookup_request__uuid=request_uuid,
        )
        response = client.request(
            url, operation_id, method="POST", expected_status=201, json=request.data
        )
        return Response(response, status=status.HTTP_201_CREATED)


@extend_schema_view(
    post=remote_kownsl_create_schema(
        "/api/v1/review-requests/{parent_lookup_request__uuid}/advices"
    ),
)
class AdviceRequestView(BaseRequestView):
    _operation_id = "advice_create"

    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)

    get.schema_summary = _("Retrieve advice review request")


AdviceRequestView.post.schema_summary = _("Register advice for review request")


@extend_schema_view(
    post=remote_kownsl_create_schema(
        "/api/v1/review-requests/{parent_lookup_request__uuid}/approvals"
    ),
)
class ApprovalRequestView(BaseRequestView):
    _operation_id = "approval_create"

    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)

    get.schema_summary = _("Retrieve approval review request")


ApprovalRequestView.post.schema_summary = _("Register approval for review request")


class ZaakReviewRequestSummaryView(GetZaakMixin, APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated & CanReadZaken,)
    schema_summary = _("List review requests summary for a case")

    def get_serializer(self, **kwargs):
        return ZaakRevReqSummarySerializer(many=True, **kwargs)

    def get(self, request, *args, **kwargs):
        zaak = self.get_object()
        review_requests = get_review_requests(zaak)
        serializer = self.get_serializer(instance=review_requests)
        return Response(serializer.data)


class ZaakReviewRequestDetailView(APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated & CanReadZaken,)
    serializer_class = ZaakRevReqDetailSerializer
    schema_summary = _("Retrieve review request details")

    def get(self, request, request_uuid, *args, **kwargs):
        review_request = get_review_request(request_uuid)

        try:
            zaak = get_zaak(review_request.for_zaak)

        except ObjectDoesNotExist:
            raise Http404(f"No zaak is found for url: {review_request.for_zaak}.")

        self.check_object_permissions(self.request, zaak)

        with parallel() as executor:

            review_request.advices = []
            if review_request.num_advices:
                _advices = executor.submit(retrieve_advices, review_request)
                review_request.advices = _advices.result()

            review_request.approvals = []
            if review_request.num_approvals:
                _approvals = executor.submit(retrieve_approvals, review_request)
                review_request.approvals = _approvals.result()

        serializer = self.serializer_class(instance=review_request)
        return Response(serializer.data)
