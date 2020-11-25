from django.urls import path

from .views import AdresSearchView, PandFetchView, VerblijfsobjectFetchView

urlpatterns = [
    path("autocomplete/adres", AdresSearchView.as_view(), name="adres-autocomplete"),
    path("adres/pand", PandFetchView.as_view(), name="adres-pand"),
    path(
        "adres/verblijfsobject",
        VerblijfsobjectFetchView.as_view(),
        name="adres-verblijfsobject",
    ),
]
