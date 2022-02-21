from django.urls import path

from .views import (
    GetBPMNView,
    ProcessInstanceFetchView,
    SendMessageView,
    SetTaskAssigneeView,
    UserTaskHistoryView,
    UserTaskView,
)

urlpatterns = [
    path(
        "fetch-process-instances",
        ProcessInstanceFetchView.as_view(),
        name="fetch-process-instances",
    ),
    path(
        "task-data/<uuid:task_id>",
        UserTaskView.as_view(),
        name="user-task-data",
    ),
    path("send-message", SendMessageView.as_view(), name="send-message"),
    path("claim-task", SetTaskAssigneeView.as_view(), name="claim-task"),
    path("bpmn/<str:process_definition_id>", GetBPMNView.as_view(), name="bpmn"),
    path(
        "task-data/historical", UserTaskHistoryView.as_view(), name="user-task-history"
    ),
]
