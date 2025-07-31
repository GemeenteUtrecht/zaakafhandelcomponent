from django.urls import include, path

from rest_framework.routers import SimpleRouter

from ..management.urls import urls as management_urls
from .views import (
    GetZakenView,
    ListZaakDocumentsESView,
    QuickSearchView,
    SearchReportViewSet,
    SearchView,
    VGUReportView,
)

router = SimpleRouter()
router.register(r"reports", SearchReportViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("management/", include(management_urls)),
    path("zaken/autocomplete", GetZakenView.as_view(), name="zaken-search"),
    path("zaken", SearchView.as_view(), name="search"),
    path("quick-search", QuickSearchView.as_view(), name="quick-search"),
    path(
        "cases/<str:bronorganisatie>/<str:identificatie>/documents",
        ListZaakDocumentsESView.as_view(),
        name="zaak-documents-es",
    ),
    path(
        "vgu-reports",
        VGUReportView.as_view(),
        name="vgu-reports",
    ),
]
