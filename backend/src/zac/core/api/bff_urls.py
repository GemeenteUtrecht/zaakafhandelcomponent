from django.urls import include, path

from .views import (
    CreateZaakRelationView,
    CreateZaakView,
    EigenschappenView,
    InformatieObjectTypeListView,
    ListZaakDocumentsView,
    ObjectSearchView,
    ObjecttypeListView,
    ObjecttypeVersionReadView,
    RelatedZakenView,
    StatusTypenView,
    VertrouwelijkheidsAanduidingenView,
    ZaakAtomicPermissionsView,
    ZaakDetailView,
    ZaakDocumentView,
    ZaakEigenschapDetailView,
    ZaakEigenschappenView,
    ZaakObjectChangeView,
    ZaakObjectsView,
    ZaakRolesView,
    ZaakStatusesView,
    ZaakTypenView,
)

urlpatterns = [
    # core zgw
    path("cases", CreateZaakView.as_view(), name="zaak-create"),
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
        "cases/properties",
        ZaakEigenschapDetailView.as_view(),
        name="zaak-properties-detail",
    ),
    path(
        "cases/<str:bronorganisatie>/<str:identificatie>/documents",
        ListZaakDocumentsView.as_view(),
        name="zaak-documents",
    ),
    path(
        "cases/document",
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
    path(
        "cases/<str:bronorganisatie>/<str:identificatie>/atomic-permissions",
        ZaakAtomicPermissionsView.as_view(),
        name="zaak-atomic-permissions",
    ),
    path(
        "cases/<str:bronorganisatie>/<str:identificatie>",
        include("zac.core.camunda.start_process.urls"),
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
    path("objecttypes", ObjecttypeListView.as_view(), name="objecttypes-list"),
    path(
        "objecttypes/<str:uuid>/versions/<int:version>",
        ObjecttypeVersionReadView.as_view(),
        name="objecttypesversion-read",
    ),
    path(
        "objects",
        ObjectSearchView.as_view(),
        name="object-search",
    ),
    path(
        "zaakobjects",
        ZaakObjectChangeView.as_view(),
        name="zaakobject-create",
    ),
    path("statustypes", StatusTypenView.as_view(), name="statustypen-list"),
]
