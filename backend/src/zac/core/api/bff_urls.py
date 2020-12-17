from django.urls import path

from .views import ZaakDetailView

urlpatterns = [
    path(
        "cases/<str:bronorganisatie>/<str:identificatie>",
        ZaakDetailView.as_view(),
        name="zaak-detail",
    ),
]
