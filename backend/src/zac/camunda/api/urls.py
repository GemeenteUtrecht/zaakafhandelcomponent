from django.urls import path

from .views import ProcessInstanceFetchView, SendMessageView, UserTaskView

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
]
