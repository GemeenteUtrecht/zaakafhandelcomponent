from django.urls import path

from .views import NotificationCallbackView

app_name = "notifications"

urlpatterns = [
    path(
        "v1/notification-callbacks", NotificationCallbackView.as_view(), name="callback"
    ),
]
