from django.urls import path

from .views import ContezzaDocumentView

app_name = "contezza"

urlpatterns = [
    path(
        "<str:bronorganisatie>/<str:identificatie>",
        ContezzaDocumentView.as_view(),
        name="contezza-document",
    ),
]
