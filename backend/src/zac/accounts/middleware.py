from django.conf import settings


class HijackMiddleware:
    header = settings.HIJACK_HEADER

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # add hijack header for FE
        is_hijacked = request.session.get("is_hijacked_user", False)
        response[self.header] = "true" if is_hijacked else "false"

        return response
