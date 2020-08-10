from rest_framework.routers import DefaultRouter

from .viewsets import UserViewSet

router = DefaultRouter(trailing_slash=False)
router.register("users", UserViewSet)

urlpatterns = router.urls
