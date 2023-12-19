from django.urls import path

from .views import (
    SubmitReviewView,
    ZaakReviewRequestDetailView,
    ZaakReviewRequestReminderView,
    ZaakReviewRequestSummaryView,
)

app_name = "kownsl"

urlpatterns = [
    path(
        "review-requests/<uuid:request_uuid>/review",
        SubmitReviewView.as_view(),
        name="reviewrequest-review",
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
