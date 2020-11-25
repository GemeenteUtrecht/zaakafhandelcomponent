from django.urls import include, path

from .views import (
    AdviceRequestView,
    ApprovalRequestView,
    MockAdviceRequestView,
    MockApprovalRequestView,
)

urlpatterns = [
    path(
        "review-requests/mock/advice",
        MockAdviceRequestView.as_view(),
        name="reviewrequest-advice-mock",
    ),
    path(
        "review-requests/mock/approval",
        MockApprovalRequestView.as_view(),
        name="reviewrequest-approval-mock",
    ),
    path(
        "review-requests/<uuid:request_uuid>/advice",
        AdviceRequestView.as_view(),
        name="reviewrequest-advice",
    ),
    path(
        "review-requests/<uuid:request_uuid>/approval",
        ApprovalRequestView.as_view(),
        name="reviewrequest-approval",
    ),
]
