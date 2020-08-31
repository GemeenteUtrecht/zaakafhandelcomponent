from django.urls import path, re_path

from .views import AddDocumentView, GetDocumentInfoView, GetInformatieObjectTypenView, GetExtraInfoSubjectView

urlpatterns = [
    path(
        "documents/get-informatieobjecttypen",
        GetInformatieObjectTypenView.as_view(),
        name="get-informatieobjecttypen",
    ),
    path("documents/upload", AddDocumentView.as_view(), name="add-document",),
    path("documents/info", GetDocumentInfoView.as_view(), name="get-document-info"),
    re_path(r'^betrokkene/(?P<bsn>[0-9]{9})/info', GetExtraInfoSubjectView.as_view(), name="get-betrokkene-info"),
]
