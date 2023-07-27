from django.conf import settings

from hijack.middleware import HijackUserMiddleware as _HijackUserMiddleware
from mozilla_django_oidc_db.middleware import SessionRefresh


class HijackUserMiddleware(_HijackUserMiddleware):
    header = settings.HIJACK_HEADER

    def process_response(self, request, response):
        response = super().process_response(request, response)
        is_hijacked = getattr(request.user, "is_hijacked", False)
        response[self.header] = "true" if is_hijacked else "false"
        return response


class HijackSessionRefresh(SessionRefresh):
    def process_request(self, request):
        if bool(request.session.get("hijack_history", [])):
            return

        return super().process_request(request)
