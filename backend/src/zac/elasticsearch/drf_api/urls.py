from django.urls import path

from .views import GetZakenView, SearchViewSet

urlpatterns = [
    path("zaken/autocomplete", GetZakenView.as_view(), name="zaken-search"),
    path("zaken", SearchViewSet.as_view(), name="search"),
]
