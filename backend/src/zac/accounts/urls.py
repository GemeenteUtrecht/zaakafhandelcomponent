from django.urls import path

from .views import LoggedInView, LoginView

app_name = "accounts"

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("logged_in/", LoggedInView.as_view(), name="logged_in"),
]
