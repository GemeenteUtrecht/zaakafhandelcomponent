from django.urls import path

from .views import (
    CreateZaakRelationView,
    EigenschappenView,
    InformatieObjectTypeListView,
    ListZaakDocumentsView,
    RelatedZakenView,
    VertrouwelijkheidsAanduidingenView,
    ZaakDetailView,
    ZaakDocumentView,
    ZaakEigenschappenView,
    ZaakObjectsView,
    ZaakRolesView,
    ZaakStatusesView,
    ZaakTypenView,
)

urlpatterns = [
    # core zgw
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
        ListZaakDocumentsView.as_view(),
        name="zaak-documents",
    ),
    path(
        "cases/<str:bronorganisatie>/<str:identificatie>/document",
        ZaakDocumentView.as_view(),
        name="zaak-document",
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
    # meta
    path("zaaktypen", ZaakTypenView.as_view(), name="zaaktypen"),
    path("eigenschappen", EigenschappenView.as_view(), name="eigenschappen"),
    path(
        "document-types",
        InformatieObjectTypeListView.as_view(),
        name="document-types-list",
    ),
    path(
        "vertrouwelijkheidsaanduidingen",
        VertrouwelijkheidsAanduidingenView.as_view(),
        name="confidentiality-classications",
    ),
]
