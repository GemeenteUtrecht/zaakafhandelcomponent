from django.urls import path

from .views import (
    CancelTaskView,
    ChangeBehandelaarTasksView,
    CreateZaakRedirectCheckView,
    FetchTaskView,
    GetBPMNView,
    ProcessInstanceFetchView,
    ProcessInstanceMessagesView,
    SendMessageView,
    SetTaskAssigneeView,
    UserTaskCountView,
    UserTaskHistoryView,
    UserTaskView,
)

urlpatterns = [
    path(
        "process-instances",
        ProcessInstanceFetchView.as_view(),
        name="fetch-process-instances",
    ),
    path("fetch-tasks", FetchTaskView.as_view(), name="fetch-tasks"),
    path(
        "fetch-messages", ProcessInstanceMessagesView.as_view(), name="fetch-messages"
    ),
    path(
        "process-instances/<uuid:id>/zaak",
        CreateZaakRedirectCheckView.as_view(),
        name="create-zaak-redirect-check",
    ),
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
    path("tasks/count", UserTaskCountView.as_view(), name="count-tasks"),
]
