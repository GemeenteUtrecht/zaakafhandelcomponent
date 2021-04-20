from django.urls import include, path

from .api import urls as api_urls
from .views import DownloadReportView, ReportsListView

app_name = "reports"

urlpatterns = [
    path("", ReportsListView.as_view(), name="report-list"),
    path("download/<int:pk>/", DownloadReportView.as_view(), name="download"),
    path("api/", include(api_urls)),
]
