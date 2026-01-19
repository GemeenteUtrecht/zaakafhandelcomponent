from django.urls import path

from .views import GetDocumentInfoView, PostExtraInfoSubjectView

urlpatterns = [
    path("documents/info", GetDocumentInfoView.as_view(), name="get-document-info"),
    path(
        "betrokkene/info",
        PostExtraInfoSubjectView.as_view(),
        name="post-betrokkene-info",
    ),
]
