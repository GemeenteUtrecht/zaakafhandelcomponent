from django.urls import path

from rest_framework.routers import DefaultRouter

from .viewsets import (
    ChecklistTypeViewSet,
    ZaakChecklistTypeViewSet,
    ZaakChecklistViewSet,
)

router = DefaultRouter(trailing_slash=False)
router.register("checklisttypes", ChecklistTypeViewSet)

urlpatterns = router.urls
urlpatterns += [
    path(
        "zaak-checklisttypes/<str:bronorganisatie>/<str:identificatie>",
        ZaakChecklistTypeViewSet.as_view({"get": "retrieve"}),
        name="zaak-checklist-type",
    ),
    path(
        "zaak-checklists/<str:bronorganisatie>/<str:identificatie>",
        ZaakChecklistViewSet.as_view(
            {"get": "retrieve", "post": "create", "put": "update"}
        ),
        name="zaak-checklist",
    ),
]
