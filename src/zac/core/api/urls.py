from django.urls import path

from .views import AddDocumentView, GetDocumentInfoView, GetInformatieObjectTypenView

urlpatterns = [
    path(
        "documents/get-informatieobjecttypen",
        GetInformatieObjectTypenView.as_view(),
        name="get-informatieobjecttypen",
    ),
    path("documents/upload", AddDocumentView.as_view(), name="add-document",),
    path("documents/info", GetDocumentInfoView.as_view(), name="get-document-info"),
]
