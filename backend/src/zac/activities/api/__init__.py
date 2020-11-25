from rest_framework.routers import DefaultRouter

from .viewsets import ActivityViewSet, EventViewSet

router = DefaultRouter(trailing_slash=False)
router.register("activities", ActivityViewSet)
router.register("events", EventViewSet)

urlpatterns = router.urls
