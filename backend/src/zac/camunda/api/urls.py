from django.urls import path

from .views import GetTaskContextView, ProcessInstanceFetchView, SendMessageView

urlpatterns = [
    path(
        "fetch-process-instances",
        ProcessInstanceFetchView.as_view(),
        name="fetch-process-instances",
    ),
    path(
        "task-data/<uuid:task_id>", GetTaskContextView.as_view(), name="get-task-data"
    ),
    path("send-message", SendMessageView.as_view(), name="send-message"),
]
