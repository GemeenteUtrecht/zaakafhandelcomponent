from rest_framework.routers import DefaultRouter

from .viewsets import ActivityViewSet

router = DefaultRouter(trailing_slash=False)
router.register("activities", ActivityViewSet)

urlpatterns = router.urls
