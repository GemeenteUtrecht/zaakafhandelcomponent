from django.urls import path

from .views import DocumentView

app_name = "doc"

urlpatterns = [
    path(
        "documents/",
        include(
            [
                path(
                    "<uuid:doc_request_uuid>/",
                    DocumentView.as_view(),
                    name="delete-document",
                ),
                path(
                    "<str:bronorganisatie>/<str:identificatie>/<str:purpose>",
                    DocumentView.as_view(),
                    name="request-document",
                ),
            ]
        ),
    ),
]
