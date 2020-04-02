from django.urls import path

from .views import AdresSearchView, PandFetchView

urlpatterns = [
    path("autocomplete/adres", AdresSearchView.as_view(), name="adres-autocomplete"),
    path("adres/pand", PandFetchView.as_view(), name="adres-pand"),
]
