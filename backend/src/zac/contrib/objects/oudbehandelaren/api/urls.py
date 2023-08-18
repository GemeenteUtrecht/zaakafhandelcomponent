from django.urls import path

from .views import OudbehandelarenView

urlpatterns = [
    path(
        "oudbehandelaren/<str:bronorganisatie>/<str:identificatie>",
        OudbehandelarenView.as_view(),
        name="zaak-oudbehandelaren",
    ),
]
