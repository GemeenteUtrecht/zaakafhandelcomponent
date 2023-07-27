from django.conf import settings
from django.utils.crypto import salted_hmac

from hijack.middleware import HijackUserMiddleware as _HijackUserMiddleware
from mozilla_django_oidc_db.middleware import SessionRefresh

from zac.accounts.models import User


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

    def process_response(self, request, response):
        response = super().process_response(request, response)
        is_hijacked = getattr(request.user, "is_hijacked", False)
        response[self.header] = "true" if is_hijacked else "false"
        return response


class HijackSessionRefresh(FirstRedirectCheckMixin, SessionRefresh):
    def process_request(self, request):
        if bool(request.session.get("hijack_history", [])):
            return

        return super().process_request(request)
