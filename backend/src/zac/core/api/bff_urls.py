from django.urls import path

from .views import ZaakDetailView, ZaakStatusesView

urlpatterns = [
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
]
