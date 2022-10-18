from django.urls import path

from rest_framework.routers import DefaultRouter

from .views import (
    CancelTaskView,
    ChangeBehandelaarTasksView,
    GetBPMNView,
    ProcessInstanceFetchViewSet,
    SendMessageView,
    SetTaskAssigneeView,
    UserTaskHistoryView,
    UserTaskView,
)

router = DefaultRouter(trailing_slash=False)
router.register(
    "fetch-process-instances",
    ProcessInstanceFetchViewSet,
    basename="fetch-process-instances",
)


urlpatterns = router.urls + [
    path(
        "task-data/<uuid:task_id>",
        UserTaskView.as_view(),
        name="user-task-data",
    ),
    path("send-message", SendMessageView.as_view(), name="send-message"),
    path("claim-task", SetTaskAssigneeView.as_view(), name="claim-task"),
    path(
        "change-behandelaar",
        ChangeBehandelaarTasksView.as_view(),
        name="change-behandelaar",
    ),
    path("bpmn/<str:process_definition_id>", GetBPMNView.as_view(), name="bpmn"),
    path(
        "task-data/historical", UserTaskHistoryView.as_view(), name="user-task-history"
    ),
    path(
        "cancel-task",
        CancelTaskView.as_view(),
        name="cancel-task",
    ),
]
