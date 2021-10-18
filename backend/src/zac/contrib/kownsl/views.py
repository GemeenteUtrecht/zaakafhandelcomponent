import datetime
import logging

from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.utils.translation import gettext_lazy as _

from django_camunda.api import complete_task
from django_camunda.client import get_client as get_camunda_client
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import authentication, permissions, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from zgw_consumers.concurrent import parallel
from zgw_consumers.models import Service

from zac.camunda.constants import AssigneeTypeChoices
from zac.core.api.permissions import CanReadZaken
from zac.core.api.views import GetZaakMixin
from zac.core.services import get_document, get_zaak
from zac.notifications.views import BaseNotificationCallbackView

from .api import (
    get_client,
    get_review_request,
    get_review_requests,
    retrieve_advices,
    retrieve_approvals,
)
from .permissions import IsReviewUser
from .serializers import (
    KownslReviewRequestSerializer,
    ZaakRevReqDetailSerializer,
    ZaakRevReqSummarySerializer,
)
from .utils import remote_kownsl_create_schema

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
        resource_url = data["hoofd_object"]
        client = Service.get_client(resource_url)
        if client is None:
            raise RuntimeError(
                f"Could not build an appropriate client for the URL {resource_url}"
            )

        logger.debug("Retrieving review request %s", resource_url)
        review_request = client.retrieve("reviewrequest", url=resource_url)

        # look up and complete the user task in Camunda
        assignee = data["kenmerken"]["group"] or data["kenmerken"]["author"]
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
    serializer_class = KownslReviewRequestSerializer

    def get_object(self):
        client = get_client(self.request.user)
        review_request = client.retrieve(
            "review_requests", uuid=self.kwargs["request_uuid"]
        )
        self.check_object_permissions(self.request, review_request)
        return review_request

    def user_has_submitted_review(self, review_request) -> str:
        # !!! Complicated and fragile logic alert !!!
        # Based on the authors and groups of submitted reviews and
        # the user_deadline field we can derive if the user is allowed to review.
        #
        # If a user has already reviewed, but is part of a group that still
        # is requested to review, the user SHOULD be allowed to submit another review
        # and even though they have already submitted, the header should be flagged as false.
        #
        # Goal:
        # Figure out if a user should be flagged as having submitted a review or not
        # based on given reviews and user_deadlines field.
        #
        # Given that:
        # 1) User_deadlines field looks like: {
        # "user:<username>"":"<deadline1_date>",
        # "group:<groupname":"<deadline2_date>",
        # etc,
        # }
        # 2) User deadlines correspond with a step uniquely (i.e., one step has 1 unique deadline)
        #
        # Steps:
        # 1) Remove the assignees that have already reviewed from user_deadlines so
        # we can figure out at which step in a serial process we are.
        # 2) Group the assignees and take out the intersection of the reviewers and assignees at that step.
        # This leaves those that still need to review.
        # If any of these are groups and the user is reviewing on behalf of that group, allow the submission of the review.
        # If the user is not part of any leftover groups at that step nor is in user_deadlines at that date
        # don't allow the submission of an(other) review.

        # Remove reviewers from assignees
        user_deadlines = {**review_request["user_deadlines"]}
        for review in review_request["reviews"]:
            if review["group"]:
                assignee = f"{AssigneeTypeChoices.group}:{review['group']}".lower()
            else:
                assignee = (
                    f"{AssigneeTypeChoices.user}:{review['author']['username']}".lower()
                )

            del user_deadlines[assignee]

        # Get users with soonest deadline
        deadlines_users = {}
        for user, deadline in user_deadlines.items():
            user = user.lower()
            try:
                deadlines_users[deadline].append(user)
            except KeyError:
                deadlines_users[deadline] = [user]

        soonest_deadline = sorted(
            list(deadlines_users.keys()),
            key=lambda datestr: datetime.datetime.fromisoformat(datestr),
        )[0]
        users = deadlines_users[soonest_deadline]
        if assignee not in users:
            return "true"
        return "false"

    def get(self, request, request_uuid):
        review_request = self.get_object()
        headers = {"X-Kownsl-Submitted": self.user_has_submitted_review(review_request)}
        zaak_url = review_request["forZaak"]
        serializer = self.serializer_class(
            instance={
                **review_request,
                "zaak": get_zaak(zaak_url=zaak_url),
            },
            context={"request": request, "view": self},
        )
        return Response(serializer.data, headers=headers)

    def post(self, request, request_uuid):
        # Check if user is allowed to get and post based on source review request user_deadlines value.
        self.get_object()
        client = get_client(request.user)
        response = client.create(
            self._operation_resource,
            data=request.data,
            request__uuid=request_uuid,
        )
        return Response(response, status=status.HTTP_201_CREATED)


@extend_schema_view(
    get=extend_schema(summary=_("Retrieve advice review request")),
    post=remote_kownsl_create_schema(
        "/api/v1/review-requests/{request__uuid}/advices",
        summary=_("Register advice for review request"),
    ),
)
class AdviceRequestView(BaseRequestView):
    _operation_resource = "review_requests_advices"


@extend_schema_view(
    get=extend_schema(summary=_("Retrieve approval review request")),
    post=remote_kownsl_create_schema(
        "/api/v1/review-requests/{request__uuid}/approvals",
        summary=_("Register approval for review request"),
    ),
)
class ApprovalRequestView(BaseRequestView):
    _operation_resource = "review_requests_approvals"


class ZaakReviewRequestSummaryView(GetZaakMixin, APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated & CanReadZaken,)

    def get_serializer(self, **kwargs):
        return ZaakRevReqSummarySerializer(many=True, **kwargs)

    @extend_schema(summary=_("List review requests summary for a case"))
    def get(self, request, *args, **kwargs):
        zaak = self.get_object()
        review_requests = get_review_requests(zaak)
        serializer = self.get_serializer(instance=review_requests)
        return Response(serializer.data)


class ZaakReviewRequestDetailView(APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (permissions.IsAuthenticated & CanReadZaken,)
    serializer_class = ZaakRevReqDetailSerializer

    @extend_schema(
        summary=_("Retrieve review request details"),
        responses={
            "200": ZaakRevReqDetailSerializer,
        },
    )
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
        serializer = self.serializer_class(instance=review_request)
        return Response(serializer.data)
