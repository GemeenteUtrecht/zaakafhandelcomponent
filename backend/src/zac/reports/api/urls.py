from django.urls import path

from .views import ReportDownloadView, ReportListViewSet

urlpatterns = [
    path("reports", ReportListViewSet.as_view(), name="report-api-list"),
    path("reports/<int:pk>", ReportDownloadView.as_view(), name="report-api-download"),
]
