from django.urls import path

from rest_framework.routers import DefaultRouter

from .views import ZaakChecklistTypeView, ZaakChecklistView

router = DefaultRouter(trailing_slash=False)

urlpatterns = router.urls
urlpatterns += [
    path(
        "zaak-checklisttypes/<str:bronorganisatie>/<str:identificatie>",
        ZaakChecklistTypeView.as_view(),
        name="zaak-checklist-type",
    ),
    path(
        "zaak-checklists/<str:bronorganisatie>/<str:identificatie>",
        ZaakChecklistView.as_view(),
        name="zaak-checklist",
    ),
]
