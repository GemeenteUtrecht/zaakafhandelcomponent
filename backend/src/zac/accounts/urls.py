from django.urls import path

from .views import DRFReleaseUserView, LoggedInView, LoginView

app_name = "accounts"

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("logged_in/", LoggedInView.as_view(), name="logged_in"),
    path("hijack/release/", DRFReleaseUserView.as_view(), name="hijack-release"),
]
