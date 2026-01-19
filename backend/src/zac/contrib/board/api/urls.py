from django.urls import path

from rest_framework.routers import DefaultRouter

from .views import (
    BoardItemViewSet,
    BoardViewSet,
    ManagementDashboardDetailView,
    ManagementDashboardSummaryView,
)

router = DefaultRouter(trailing_slash=False)
router.register("boards", BoardViewSet)
router.register("items", BoardItemViewSet)


urlpatterns = router.urls + [
    path(
        "management",
        ManagementDashboardDetailView.as_view(),
        name="management-dashboard",
    ),
    path(
        "management/summary",
        ManagementDashboardSummaryView.as_view(),
        name="management-dashboard-summary",
    ),
]
