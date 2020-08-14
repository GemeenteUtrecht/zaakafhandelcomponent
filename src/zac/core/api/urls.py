from django.urls import path

from .views import AddDocumentView, GetInformatieObjectTypenView

urlpatterns = [
    path(
        "documents/get-informatieobjecttypen",
        GetInformatieObjectTypenView.as_view(),
        name="get-informatieobjecttypen",
    ),
    path("documents/upload", AddDocumentView.as_view(), name="add-document",),
]
