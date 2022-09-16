from rest_framework.permissions import BasePermission

from zac.accounts.models import ApplicationToken


class HasTokenAuth(BasePermission):
    def has_permission(self, request, view) -> bool:
        if request.auth and isinstance(request.auth, ApplicationToken):
            return True
        return False
