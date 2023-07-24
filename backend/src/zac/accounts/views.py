from django.conf import settings
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
        redirect_to = self.request.session.pop("login_next", "/ui")
        if getattr(self.request.user, "is_hijacked", False):
            return settings.HIJACK_LOGIN_REDIRECT_URL
        return redirect_to
