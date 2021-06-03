from django.urls import path

from rest_framework.routers import DefaultRouter

from .views import GrantZaakPermissionView, InformatieobjecttypenJSONView
from .viewsets import UserViewSet

router = DefaultRouter(trailing_slash=False)
router.register("users", UserViewSet, basename="users")

urlpatterns = router.urls + [
    path(
        "informatieobjecttypen",
        InformatieobjecttypenJSONView.as_view(),
        name="informatieobjecttypen",
    ),
    path("cases/access", GrantZaakPermissionView.as_view(), name="grant-zaak-access"),
]
