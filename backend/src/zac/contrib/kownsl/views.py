import logging

from django_camunda.api import complete_task
from django_camunda.client import get_client as get_camunda_client
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from zds_client.client import get_operation_url
from zgw_consumers.client import ZGWClient
from zgw_consumers.models import Service

from zac.notifications.views import BaseNotificationCallbackView

from .models import KownslConfig
from .permissions import IsReviewUser

logger = logging.getLogger(__name__)


def get_client() -> ZGWClient:
    config = KownslConfig.get_solo()
    assert config.service, "A service must be configured first"
    return config.service.build_client()


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

    def get(self, request, request_uuid):
        client = get_client()
        operation_id = "reviewrequest_retrieve"
        url = get_operation_url(
            client.schema,
            operation_id,
            uuid=request_uuid,
        )
        self.rr = client.request(url, operation_id)
        self.check_object_permissions(request, self.rr)
        return Response(self.rr)

    def post(self, request, request_uuid):
        # Check if user is allowed to get and post based on source review request user_deadlines value.
        self.get(request, request_uuid)

        client = get_client()
        operation_id = self._operation_id
        url = get_operation_url(
            client.schema,
            operation_id,
            parent_lookup_request__uuid=request_uuid,
        )
        response = client.request(
            url, operation_id, method="POST", expected_status=201, json=request.data
        )
        return Response(response)


class AdviceRequestView(BaseRequestView):
    _operation_id = "advice_create"


class ApprovalRequestView(BaseRequestView):
    _operation_id = "approval_create"


import json
from datetime import datetime

### Added a temporary endpoint for frontend dev ###
from .tests.factories import (
    AdviceFactory,
    ApprovalFactory,
    ReviewRequestFactory,
    ZaakDocumentFactory,
)


class MockBaseReviewRequest(APIView):
    permission_classes = (AllowAny,)
    _operation_id = NotImplemented

    def obj_to_dict(self, obj):
        cleaned = {}
        for key, val in obj.__dict__.items():
            if isinstance(val, datetime):
                cleaned[key] = str(val)
            else:
                cleaned[key] = val

        return cleaned

    def get(self, request):
        zaak_documents = ZaakDocumentFactory.create_batch(2)
        zaak_documents = [self.obj_to_dict(zd) for zd in zaak_documents]

        rr = ReviewRequestFactory.create(
            review_type=self._operation_id,
        )
        rr = self.obj_to_dict(rr)

        if self._operation_id == "advice":
            previous = AdviceFactory.create_batch(2)
        else:
            previous = ApprovalFactory.create_batch(2)

        previous = [self.obj_to_dict(pr) for pr in previous]

        rr.update({"zaak_documents": zaak_documents, "previous": previous})

        return Response(json.dumps(rr), status=200)

    def post(self, request):
        message = {"Message": "Great success"}
        return Response(message, status=201)


class MockAdviceRequestView(MockBaseReviewRequest):
    _operation_id = "advice"


class MockApprovalRequestView(MockBaseReviewRequest):
    _operation_id = "approval"
