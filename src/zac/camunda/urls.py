from django.urls import path

from .api.views import CallbackView

app_name = "camunda"

urlpatterns = [
    path(
        "api/v1/user-task/callback/<uuid:callback_id>",
        CallbackView.as_view(),
        name="user-task-callback",
    ),
]
