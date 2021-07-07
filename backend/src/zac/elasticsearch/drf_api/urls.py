from django.urls import include, path

from rest_framework.routers import SimpleRouter

from .views import GetZakenView, SearchReportViewSet, SearchView

router = SimpleRouter()
router.register(r"reports", SearchReportViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("zaken/autocomplete", GetZakenView.as_view(), name="zaken-search"),
    path("zaken", SearchView.as_view(), name="search"),
]
