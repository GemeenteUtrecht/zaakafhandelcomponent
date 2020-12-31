from django.urls import path

from .views import (
    RelatedZakenView,
    ZaakDetailView,
    ZaakDocumentsView,
    ZaakEigenschappenView,
    ZaakStatusesView,
)

urlpatterns = [
    path(
        "cases/<str:bronorganisatie>/<str:identificatie>",
        ZaakDetailView.as_view(),
        name="zaak-detail",
    ),
    path(
        "cases/<str:bronorganisatie>/<str:identificatie>/statuses",
        ZaakStatusesView.as_view(),
        name="zaak-statuses",
    ),
    path(
        "cases/<str:bronorganisatie>/<str:identificatie>/properties",
        ZaakEigenschappenView.as_view(),
        name="zaak-properties",
    ),
    path(
        "cases/<str:bronorganisatie>/<str:identificatie>/documents",
        ZaakDocumentsView.as_view(),
        name="zaak-documents",
    ),
    path(
        "cases/<str:bronorganisatie>/<str:identificatie>/related-cases",
        RelatedZakenView.as_view(),
        name="zaak-related",
    ),
]
