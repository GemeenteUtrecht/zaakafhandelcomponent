from django.urls import path

from .views import (
    GetUserTaskContextView,
    ProcessInstanceFetchView,
    SendMessageView,
    SubmitUserTaskView,
)

urlpatterns = [
    path(
        "fetch-process-instances",
        ProcessInstanceFetchView.as_view(),
        name="fetch-process-instances",
    ),
    path(
        "task-data/<uuid:task_id>/submit",
        SubmitUserTaskView.as_view(),
        name="submit-task-data",
    ),
    path(
        "task-data/<uuid:task_id>",
        GetUserTaskContextView.as_view(),
        name="get-task-data",
    ),
    path("send-message", SendMessageView.as_view(), name="send-message"),
]
