from django.contrib.auth.views import LoginView as _LoginView


class LoginView(_LoginView):
    template_name = "accounts/login.html"
