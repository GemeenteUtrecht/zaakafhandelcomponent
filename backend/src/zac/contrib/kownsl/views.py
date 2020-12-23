import logging

from django_camunda.api import complete_task
from django_camunda.client import get_client as get_camunda_client
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from zds_client.client import get_operation_url
from zgw_consumers.models import Service

from zac.api.utils import remote_schema_ref
from zac.notifications.views import BaseNotificationCallbackView

from .api import get_client
from .permissions import IsReviewUser

logger = logging.getLogger(__name__)


KOWNSL_OAS = "https://kownsl.utrechtproeftuin.nl/api/v1"

KOWNSL_REVIEW_REQUEST_SCHEMA = [
    "paths",
    "/api/v1/review-requests/{uuid}",
    "get",
    "responses",
    "200",
    "content",
    "application/json",
    "schema",
]


KOWNSL_ADVICE_REQUEST_SCHEMA = [
    "paths",
    "/api/v1/review-requests/{parent_lookup_request__uuid}/advices",
    "post",
    "requestBody",
    "content",
    "application/json",
    "schema",
]

KOWNSL_ADVICE_RESPONSE_SCHEMA = [
    "paths",
    "/api/v1/review-requests/{parent_lookup_request__uuid}/advices",
    "post",
    "responses",
    "200",
    "content",
    "application/json",
    "schema",
]

KOWNSL_APPROVAL_REQUEST_SCHEMA = [
    "paths",
    "/api/v1/review-requests/{parent_lookup_request__uuid}/approvals",
    "post",
    "requestBody",
    "content",
    "application/json",
    "schema",
]

KOWNSL_APPROVAL_RESPONSE_SCHEMA = [
    "paths",
    "/api/v1/review-requests/{parent_lookup_request__uuid}/approvals",
    "post",
    "responses",
    "200",
    "content",
    "application/json",
    "schema",
]


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
    This view allows a user to:
    1) get relevant review request data from the kownsl API to be able to form an advice,
    2) post their advice/approval to the kownsl component.

    * Requires that the requesting user is authenticated and found in review_request.user_deadlines
    """

    permission_classes = (IsAuthenticated & IsReviewUser,)
    _operation_id = NotImplemented

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

    @extend_schema(
        responses={
            (200, "application/json"): {
                "$ref": remote_schema_ref(KOWNSL_OAS, KOWNSL_REVIEW_REQUEST_SCHEMA)
            }
        }
    )
    def get(self, request, request_uuid):
        review_request = self.get_object()
        return Response(review_request)

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
    post=extend_schema(
        request={
            "application/json": {
                "$ref": remote_schema_ref(KOWNSL_OAS, KOWNSL_ADVICE_REQUEST_SCHEMA),
            }
        },
        responses={
            (201, "application/json"): {
                "$ref": remote_schema_ref(KOWNSL_OAS, KOWNSL_ADVICE_RESPONSE_SCHEMA),
            }
        },
    )
)
class AdviceRequestView(BaseRequestView):
    _operation_id = "advice_create"


@extend_schema_view(
    post=extend_schema(
        request={
            "application/json": {
                "$ref": remote_schema_ref(KOWNSL_OAS, KOWNSL_APPROVAL_REQUEST_SCHEMA),
            }
        },
        responses={
            (201, "application/json"): {
                "$ref": remote_schema_ref(KOWNSL_OAS, KOWNSL_APPROVAL_RESPONSE_SCHEMA),
            }
        },
    )
)
class ApprovalRequestView(BaseRequestView):
    _operation_id = "approval_create"
