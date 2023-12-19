import logging

from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _

from django_camunda.api import send_message
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import authentication, exceptions, permissions, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from zac.core.api.permissions import CanReadZaken
from zac.core.api.views import GetZaakMixin
from zac.core.camunda.utils import resolve_assignee
from zac.core.services import get_zaak

from ...services import (
    get_all_review_requests_for_zaak,
    get_review_request,
    get_reviews_for_zaak,
    lock_review_request,
    submit_review,
    update_review_request,
)
from ..cache import invalidate_review_cache, invalidate_review_requests_cache
from ..data import ReviewRequest
from ..permissions import (
    CanReadOrUpdateReviews,
    HasNotReviewed,
    IsReviewUser,
    ReviewIsNotBeingReconfigured,
    ReviewIsUnlocked,
)
from .serializers import (
    SubmitReviewSerializer,
    UpdateZaakReviewRequestSerializer,
    ZaakRevReqDetailSerializer,
    ZaakRevReqSummarySerializer,
)

logger = logging.getLogger(__name__)


class GetReviewRequestMixin:
    def get_object(self) -> ReviewRequest:
        if not hasattr(self, "_review_request"):
            rr = get_review_request(self.kwargs["request_uuid"])
            if not rr:
                raise exceptions.NotFound(
                    f"Could not find a review request with `uuid`: `{self.kwargs['request_uuid']}`."
                )
            self.check_object_permissions(self.request, rr)
            self._review_request = rr
        return self._review_request


class SubmitReviewView(GetReviewRequestMixin, APIView):
    """
    This view allows a user to get relevant review request data from the kownsl API to be able to form an advice,
    and post their advice/approval to the kownsl component.

    * Requires that the requesting user is authenticated and found in review_request.user_deadlines and an
    assignee parameter is found in both the get as well as the post.
    """

    permission_classes = (
        IsAuthenticated,
        IsReviewUser,
        HasNotReviewed,
        ReviewIsUnlocked,
    )
    serializer_class = ZaakRevReqDetailSerializer

    @extend_schema(
        summary=_("Retrieve review request."),
        parameters=[
            OpenApiParameter(
                name="assignee",
                required=True,
                type=OpenApiTypes.STR,
                description=_("Assignee of the user task in camunda."),
                location=OpenApiParameter.QUERY,
            )
        ],
        responses={200: ZaakRevReqDetailSerializer},
    )
    def get(self, request, request_uuid):
        if not (request.query_params.get("assignee")):
            raise exceptions.ValidationError("'assignee' query parameter is required.")

        review_request = self.get_object()
        review_request.zaak = get_zaak(zaak_url=review_request.zaak)
        serializer = self.serializer_class(
            instance=review_request,
            context={"request": request, "view": self},
        )
        return Response(serializer.data)

    @extend_schema(
        summary=_("Create review for review request."),
        parameters=[
            OpenApiParameter(
                name="assignee",
                required=True,
                type=OpenApiTypes.STR,
                description=_("Assignee of the user task in camunda."),
                location=OpenApiParameter.QUERY,
            )
        ],
        request=SubmitReviewSerializer,
        responses={201: SubmitReviewSerializer(many=True)},
    )
    def post(self, request, request_uuid):
        if not (assignee := request.query_params.get("assignee")):
            raise exceptions.ValidationError("'assignee' query parameter is required.")

        data = {**request.data}
        assignee = resolve_assignee(assignee)
        if isinstance(assignee, Group):
            data["group"] = f"{assignee}"

        rr = self.get_object()  # check permissions
        data["review_type"] = rr.review_type
        serializer = SubmitReviewSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        reviews = submit_review(serializer.data, review_request=rr)
        invalidate_review_cache(rr)
        return Response(SubmitReviewSerializer(reviews.reviews, many=True).data)


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
        review_requests = get_all_review_requests_for_zaak(zaak)
        if review_requests:
            # resolve relations
            reviews = {}
            for review in get_reviews_for_zaak(zaak):
                if review.review_request in reviews:
                    reviews[review.review_request].append(review.reviews)
                else:
                    reviews[review.review_request] = [review.reviews]

            for rr in review_requests:
                rr.reviews = sorted(
                    reviews.get(str(rr.id), []), key=lambda x: x.created, reverse=True
                )
                rr.fetched_reviews = True

        serializer = self.get_serializer(
            instance=review_requests, context={"request": request}
        )
        return Response(serializer.data)


class ZaakReviewRequestDetailView(GetReviewRequestMixin, APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (
        permissions.IsAuthenticated,
        CanReadOrUpdateReviews,
        ReviewIsUnlocked,
        ReviewIsNotBeingReconfigured,
    )

    @extend_schema(
        summary=_("Retrieve review request."),
        responses={
            200: ZaakRevReqDetailSerializer,
        },
    )
    def get(self, *args, **kwargs):
        # check permissions
        review_request = self.get_object()

        # resolve zaak
        review_request.zaak = get_zaak(zaak_url=review_request.zaak)

        # serialize
        serializer = ZaakRevReqDetailSerializer(instance=review_request)
        return Response(serializer.data)

    @extend_schema(
        summary=_("Partially update the review request."),
        request=UpdateZaakReviewRequestSerializer,
        responses={
            200: ZaakRevReqSummarySerializer,
        },
    )
    def patch(self, request, request_uuid, *args, **kwargs):
        # check permissions
        review_request = self.get_object()

        # serialize
        serializer = UpdateZaakReviewRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # figure out if the call was used to lock or update
        if lock_reason := serializer.validated_data.get("lock_reason"):
            review_request = lock_review_request(
                request_uuid, lock_reason=lock_reason, requester=request.user
            )

        elif serializer.validated_data.get("update_users"):
            send_message(
                "change-process", [review_request.metadata["process_instance_id"]]
            )
            review_request = update_review_request(
                review_request.id,
                request.user,
                data={
                    "is_being_reconfigured": True,
                },
            )

        # invalidate cache after updating
        invalidate_review_requests_cache(review_request)

        # serialize
        response_serializer = ZaakRevReqSummarySerializer(instance=review_request)
        return Response(response_serializer.data)


class ZaakReviewRequestReminderView(GetReviewRequestMixin, APIView):
    authentication_classes = (authentication.SessionAuthentication,)
    permission_classes = (
        permissions.IsAuthenticated,
        CanReadOrUpdateReviews,
        ReviewIsUnlocked,
    )

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
