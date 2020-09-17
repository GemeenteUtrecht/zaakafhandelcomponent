from django.urls import path, re_path

from .views import (
    AddDocumentView,
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
    path(
        "betrokkene/info",
        PostExtraInfoSubjectView.as_view(),
        name="post-betrokkene-info",
    ),
]
