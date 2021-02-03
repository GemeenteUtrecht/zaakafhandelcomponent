from django.urls import path

from .views import (
    CreateZaakRelationView,
    EigenschappenView,
    RelatedZakenView,
    ZaakDetailView,
    ZaakDocumentsView,
    ZaakEigenschappenView,
    ZaakObjectsView,
    ZaakRolesView,
    ZaakStatusesView,
    ZaakTypenView,
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
    path(
        "cases/related-case", CreateZaakRelationView.as_view(), name="add-zaak-relation"
    ),
    path(
        "cases/<str:bronorganisatie>/<str:identificatie>/roles",
        ZaakRolesView.as_view(),
        name="zaak-roles",
    ),
    path(
        "cases/<str:bronorganisatie>/<str:identificatie>/objects",
        ZaakObjectsView.as_view(),
        name="zaak-objects",
    ),
    path("zaaktypen", ZaakTypenView.as_view(), name="zaaktypen"),
    path("eigenschappen", EigenschappenView.as_view(), name="eigenschappen"),
]
