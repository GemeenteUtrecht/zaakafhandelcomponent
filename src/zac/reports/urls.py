from django.urls import path

from .views import DownloadReportView

app_name = "reports"

urlpatterns = [
    path("download/<int:pk>/", DownloadReportView.as_view(), name="download")
]
