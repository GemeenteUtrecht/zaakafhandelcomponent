from django.contrib.auth.views import LoginView as _LoginView
from django.views.generic import RedirectView


class LoginView(_LoginView):
    template_name = "accounts/login.html"

    def get(self, request, *args, **kwargs):
        login_next = self.request.GET.get("next")
        request.session["login_next"] = login_next
        return super().get(request, *args, **kwargs)


class LoggedInView(RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        return self.request.session.pop("login_next", "/ui")
