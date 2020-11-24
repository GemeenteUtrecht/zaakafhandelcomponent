from django.urls import include, path

from .views import AdviceRequestView, ApprovalRequestView

urlpatterns = [
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
