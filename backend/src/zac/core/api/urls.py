from django.urls import path

from .views import (
    AddDocumentView,
    AddZaakRelationView,
    GetDocumentInfoView,
    GetInformatieObjectTypenView,
    PostExtraInfoSubjectView,
)

urlpatterns = [
    path(
        "documents/get-informatieobjecttypen",
        GetInformatieObjectTypenView.as_view(),
        name="get-informatieobjecttypen",
    ),
    path(
        "documents/upload",
        AddDocumentView.as_view(),
        name="add-document",
    ),
    path("documents/info", GetDocumentInfoView.as_view(), name="get-document-info"),
    path("zaken_relation", AddZaakRelationView.as_view(), name="add-zaak-relation"),
    path(
        "betrokkene/info",
        PostExtraInfoSubjectView.as_view(),
        name="post-betrokkene-info",
    ),
]
