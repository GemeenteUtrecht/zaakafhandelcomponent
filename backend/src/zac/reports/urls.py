from django.urls import path

from .views import DownloadReportView, ReportsListView

app_name = "reports"

urlpatterns = [
    path("", ReportsListView.as_view(), name="report-list"),
    path("download/<int:pk>/", DownloadReportView.as_view(), name="download"),
]
