from django.urls import path

from .views import (
    AdresSearchView,
    FindPand,
    NummerAanduidingView,
    PandView,
    VerblijfsobjectFetchView,
)

app_name = "kadaster"

urlpatterns = [
    path("autocomplete/adres", AdresSearchView.as_view(), name="adres-autocomplete"),
    path("adres/pand", FindPand.as_view(), name="adres-pand"),
    path(
        "adres/verblijfsobject",
        VerblijfsobjectFetchView.as_view(),
        name="adres-verblijfsobject",
    ),
    path("panden/<str:pandidentificatie>", PandView.as_view(), name="pand"),
    path(
        "nummeraanduidingen/<str:nummeraanduidingidentificatie>",
        NummerAanduidingView.as_view(),
        name="nummeraanduiding",
    ),
]
