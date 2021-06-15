from django.urls import path

from rest_framework.routers import DefaultRouter

from .views import InformatieobjecttypenJSONView
from .viewsets import AccessRequestViewSet, AtomicPermissionViewSet, UserViewSet

router = DefaultRouter(trailing_slash=False)
router.register("users", UserViewSet, basename="users")
router.register("access-requests", AccessRequestViewSet)
router.register("cases/access", AtomicPermissionViewSet, basename="accesses")

urlpatterns = router.urls + [
    path(
        "informatieobjecttypen",
        InformatieobjecttypenJSONView.as_view(),
        name="informatieobjecttypen",
    ),
]
