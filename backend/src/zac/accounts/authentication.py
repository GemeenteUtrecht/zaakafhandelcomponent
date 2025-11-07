from django.utils.translation import gettext_lazy as _

from rest_framework import exceptions
from rest_framework.authentication import TokenAuthentication as _TokenAuthentication


class ApplicationTokenAuthentication(_TokenAuthentication):
    keyword = "ApplicationToken"

    def authenticate_credentials(self, key):
        from .models import ApplicationToken

        try:
            token = ApplicationToken.objects.get(token=key)
        except ApplicationToken.DoesNotExist:
            raise exceptions.AuthenticationFailed(_("Invalid token."))

        return (None, token)
