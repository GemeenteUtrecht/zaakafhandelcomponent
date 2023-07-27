from django.contrib.auth.views import LoginView as _LoginView
from django.http import HttpResponse
from django.views.generic import RedirectView

from hijack.views import ReleaseUserView
from rest_framework.status import HTTP_204_NO_CONTENT


class LoginView(_LoginView):
    template_name = "accounts/login.html"

    def get(self, request, *args, **kwargs):
        login_next = self.request.GET.get("next")
        request.session["login_next"] = login_next
        return super().get(request, *args, **kwargs)


class LoggedInView(RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        redirect_to = self.request.session.pop("login_next", "/ui")
        return redirect_to


class DRFReleaseUserView(ReleaseUserView):
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if 200 <= response.status_code < 400:
            return HttpResponse(status=HTTP_204_NO_CONTENT)
        else:
            return response
