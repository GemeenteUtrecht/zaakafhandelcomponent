import logging

from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest
from django.urls import reverse
from django.utils.functional import SimpleLazyObject

from rest_framework import exceptions
from rest_framework.authentication import TokenAuthentication

logger = logging.getLogger(__name__)


def get_user(request):
    if not hasattr(request, "_cached_scim_user"):
        token_auth = TokenAuthentication()
        user = None
        try:
            auth = token_auth.authenticate(request)
            if auth is not None:
                user, token = auth
        except exceptions.AuthenticationFailed:
            logger.warning(
                "Unauthenticated SCIM v2 request", extra={"request": request}
            )
        request._cached_scim_user = user or AnonymousUser()
    return request._cached_scim_user


class SCIMAuthMiddleware:
    """
    Use DRF Token Auth for SCIM endpoint authentication.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    @property
    def reverse_url(self):  # taken from django-scim middleware
        if not hasattr(self, "_reverse_url"):
            self._reverse_url = reverse("scim:root")
        return self._reverse_url

    def __call__(self, request: HttpRequest):
        # only authenticate if they are SCIM endpoints and the user is not authenticated yet
        if (not request.user or request.user.is_anonymous) and request.path.startswith(
            self.reverse_url
        ):
            request.user = SimpleLazyObject(lambda: get_user(request))
        return self.get_response(request)
