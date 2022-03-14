from rest_framework.routers import DefaultRouter

from .viewsets import ChecklistTypeViewSet, ChecklistViewSet

router = DefaultRouter(trailing_slash=False)
router.register("checklists", ChecklistViewSet)
router.register("checklisttypes", ChecklistTypeViewSet)

urlpatterns = router.urls
