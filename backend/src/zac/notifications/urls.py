from django.urls import path

from zac.contrib.kownsl.views import KownslNotificationCallbackView

from .views import NotificationCallbackView

app_name = "notifications"

urlpatterns = [
    path(
        "v1/notification-callbacks", NotificationCallbackView.as_view(), name="callback"
    ),
    path(
        "v1/kownsl-callbacks",
        KownslNotificationCallbackView.as_view(),
        name="kownsl-callback",
    ),
]
