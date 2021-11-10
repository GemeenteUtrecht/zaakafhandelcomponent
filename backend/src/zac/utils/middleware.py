from django.conf import settings
from django.http import HttpResponse


class ReleaseHeaderMiddleware:
    """
    Add HTTP response headers including release/version information.
    """

    RELEASE_HEADER = "X-Release"
    GIT_SHA_HEADER = "X-Git-Sha"

    def __init__(self, get_response=None):
        self.get_response = get_response

    def __call__(self, request):
        if self.get_response is None:
            return None

        response = self.get_response(request)
        if not isinstance(response, HttpResponse):
            return response

        # set the headers
        response[self.RELEASE_HEADER] = settings.RELEASE
        response[self.GIT_SHA_HEADER] = settings.GIT_SHA

        return response
