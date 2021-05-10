from django.urls import path

from .views import ReportDownloadView, ReportListViewSet

urlpatterns = [
    path("", ReportListViewSet.as_view(), name="report-api-list"),
    path("<int:pk>", ReportDownloadView.as_view(), name="report-api-download"),
]
