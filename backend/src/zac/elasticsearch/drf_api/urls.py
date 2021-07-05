from django.urls import include, path

from rest_framework.routers import SimpleRouter

from .views import GetZakenView, SearchReportDetailView, SearchReportViewSet, SearchView

router = SimpleRouter()
router.register(r"reports", SearchReportViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path(
        "reports/<int:pk>/results",
        SearchReportDetailView.as_view(),
        name="searchreport-results",
    ),
    path("zaken/autocomplete", GetZakenView.as_view(), name="zaken-search"),
    path("zaken", SearchView.as_view(), name="search"),
]
