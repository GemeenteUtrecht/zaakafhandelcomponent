from django.urls import include, path

from rest_framework.routers import DefaultRouter

from ..management.urls import urls as management_urls
from .views import (
    EditLockZaakChecklistView,
    EditUnlockZaakChecklistView,
    ZaakChecklistTypeView,
    ZaakChecklistView,
)

router = DefaultRouter(trailing_slash=False)

urlpatterns = router.urls
urlpatterns += [
    path("management/", include(management_urls)),
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
    path(
        "zaak-checklists/<str:bronorganisatie>/<str:identificatie>/lock",
        EditLockZaakChecklistView.as_view(),
        name="lock-zaak-checklist",
    ),
    path(
        "zaak-checklists/<str:bronorganisatie>/<str:identificatie>/unlock",
        EditUnlockZaakChecklistView.as_view(),
        name="unlock-zaak-checklist",
    ),
]
