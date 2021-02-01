from django.core.exceptions import ImproperlyConfigured

from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView

from zac.core.permissions import Permission


class RulesPermission(permissions.BasePermission):
    """
    Wrap the rules-based permissions.
    """

    permission: Permission

    def __new__(cls, *args, **kwargs):
        permission = getattr(cls, "permission", None)
        if permission is None:
            raise ImproperlyConfigured(
                "%s is missing the 'permission' attribute" % cls.__name__
            )
        return super().__new__(cls, *args, **kwargs)

    def has_permission(self, request: Request, view: APIView) -> bool:
        return request.user.has_perm(self.permission.name)

    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        return request.user.has_perm(self.permission.name, obj)
