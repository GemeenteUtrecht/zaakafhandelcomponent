import logging
from typing import Union

from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from django.utils.translation import gettext_lazy as _

from django_camunda.api import complete_task
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

from zac.accounts.models import User
from zac.camunda.constants import AssigneeTypeChoices
from zac.core.api.permissions import CanReadZaken
from zac.core.api.views import GetZaakMixin
from zac.core.camunda.utils import resolve_assignee
from zac.core.services import get_document, get_zaak
from zac.notifications.views import BaseNotificationCallbackView

from .api import (
    get_client,
    get_review_request,
    get_review_requests,
    retrieve_advices,
    retrieve_approvals,
)
from .constants import KownslTypes
from .data import ReviewRequest
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
        if data["kenmerken"]["group"]:
            assignee = f'{AssigneeTypeChoices.group}:{data["kenmerken"]["group"]}'
        else:
            assignee = f'{AssigneeTypeChoices.user}:{data["kenmerken"]["author"]}'

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
                "No user tasks found - possibly they were already marked completed. "
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

    def check_if_review_is_already_given(
        self, rr: ReviewRequest, assignee: Union[User, Group]
    ):
        if rr.review_type == KownslTypes.advice:
            reviews = retrieve_advices(rr)
        else:
            reviews = retrieve_approvals(rr)

        error_msg = "Review for review request `%s` is already given by assignee `%s`."
        for review in reviews:
            if review.group:
                if assignee.name == review.group:
                    raise exceptions.ValidationError(error_msg % (rr.id, assignee.name))
            else:
                if assignee.username == review.author.username:
                    raise exceptions.ValidationError(
                        error_msg % (rr.id, assignee.username)
                    )

    def get(self, request, request_uuid):
        if not (assignee := request.query_params.get("assignee")):
            raise exceptions.ValidationError("'assignee' query parameter is required.")

        assignee = resolve_assignee(assignee)
        review_request = self.get_object()
        self.check_if_review_is_already_given(
            factory(ReviewRequest, review_request), assignee
        )

        zaak_url = review_request["forZaak"]
        serializer = self.serializer_class(
            instance={
                **review_request,
                "zaak": get_zaak(zaak_url=zaak_url),
            },
            context={"request": request, "view": self},
        )
        return Response(serializer.data)

    def post(self, request, request_uuid):
        if not (assignee := request.query_params.get("assignee")):
            raise exceptions.ValidationError("'assignee' query parameter is required.")

        assignee = resolve_assignee(assignee)
        data = {**request.data}
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


ASSIGNEE_PARAMETER = (
    OpenApiParameter(
        name="assignee",
        required=True,
        type=OpenApiTypes.STR,
        description=_("Assignee of the user task in camunda."),
        location=OpenApiParameter.QUERY,
    ),
)


@extend_schema_view(
    get=extend_schema(
        summary=_("Retrieve advice review request"),
        parameters=[ASSIGNEE_PARAMETER],
    ),
    post=remote_kownsl_create_schema(
        "/api/v1/review-requests/{request__uuid}/advices",
        summary=_("Register advice for review request"),
        parameters=[ASSIGNEE_PARAMETER],
    ),
)
class AdviceRequestView(BaseRequestView):
    _operation_resource = "review_requests_advices"


@extend_schema_view(
    get=extend_schema(
        summary=_("Retrieve approval review request"),
        parameters=[ASSIGNEE_PARAMETER],
    ),
    post=remote_kownsl_create_schema(
        "/api/v1/review-requests/{request__uuid}/approvals",
        summary=_("Register approval for review request"),
        parameters=[ASSIGNEE_PARAMETER],
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
