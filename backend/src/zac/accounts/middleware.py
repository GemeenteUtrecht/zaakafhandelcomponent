import logging

from django.conf import settings
from django.urls import reverse_lazy
from django.utils.crypto import salted_hmac

from hijack.middleware import HijackUserMiddleware as _HijackUserMiddleware
from mozilla_django_oidc_db.middleware import SessionRefresh

from zac.accounts.models import User

logger = logging.getLogger(__name__)


class FirstRedirectCheckMixin:
    key_salt = settings.SECRET_KEY

    def _make_hash_value(self, user: User) -> str:
        """
        Hash the:
            user primary key and password,

        """
        return str(user.pk) + user.password

    def make_first_redirect_key(self, user: User) -> str:
        return salted_hmac(
            self.key_salt,
            self._make_hash_value(user),
        ).hexdigest()[::2]


class HijackUserMiddleware(FirstRedirectCheckMixin, _HijackUserMiddleware):
    header = settings.HIJACK_HEADER
    release_url = reverse_lazy("hijack:release")

    def process_request(self, request):
        super().process_request(request)
        if request.path == self.release_url and request.method == "POST":
            request.session[
                "first_redirect_after_hijack"
            ] = self.make_first_redirect_key(request.user)

    def process_response(self, request, response):
        response = super().process_response(request, response)
        is_hijacked = getattr(request.user, "is_hijacked", False)
        response[self.header] = "true" if is_hijacked else "false"
        return response


class HijackSessionRefresh(FirstRedirectCheckMixin, SessionRefresh):
    def process_request(self, request):
        first_redirect = request.session.get("first_redirect_after_hijack", False)
        if first_redirect and first_redirect == self.make_first_redirect_key(
            request.user
        ):
            del request.session["first_redirect_after_hijack"]
            return

        if bool(request.session.get("hijack_history", [])):
            return

        return super().process_request(request)
