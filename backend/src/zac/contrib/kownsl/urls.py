from django.urls import path

from .views import (
    AdviceRequestView,
    ApprovalRequestView,
    ZaakReviewRequestDetailView,
    ZaakReviewRequestReminderView,
    ZaakReviewRequestSummaryView,
)

app_name = "kownsl"

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
    path(
        "zaak-review-requests/<str:bronorganisatie>/<str:identificatie>/summary",
        ZaakReviewRequestSummaryView.as_view(),
        name="zaak-review-requests-summary",
    ),
    path(
        "zaak-review-requests/<uuid:request_uuid>/detail",
        ZaakReviewRequestDetailView.as_view(),
        name="zaak-review-requests-detail",
    ),
    path(
        "zaak-review-requests/<uuid:request_uuid>/reminder",
        ZaakReviewRequestReminderView.as_view(),
        name="zaak-review-requests-reminder",
    ),
]
