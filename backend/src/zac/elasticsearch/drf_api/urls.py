from django.urls import path

from .views import GetZakenView, SearchReportDetailView, SearchReportViewSet, SearchView

urlpatterns = [
    path("reports", SearchReportViewSet.as_view(), name="report-list"),
    path("reports/<int:pk>", SearchReportDetailView.as_view(), name="report-detail"),
    path("zaken/autocomplete", GetZakenView.as_view(), name="zaken-search"),
    path("zaken", SearchView.as_view(), name="search"),
]
