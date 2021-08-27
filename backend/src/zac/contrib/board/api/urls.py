from rest_framework.routers import DefaultRouter

from .views import BoardItemViewSet, BoardViewSet

router = DefaultRouter(trailing_slash=False)
router.register("boards", BoardViewSet)
router.register("items", BoardItemViewSet)


urlpatterns = router.urls
