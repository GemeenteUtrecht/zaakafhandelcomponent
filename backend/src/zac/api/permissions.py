import logging

from django.core.exceptions import ImproperlyConfigured

from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView
from zds_client import ClientError

from zac.core.permissions import Permission
from zac.core.services import get_zaak

logger = logging.getLogger(__name__)


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


class ZaakBasedPermission(permissions.BasePermission):
    permission: Permission
    zaak_attr = "zaak"

    def __new__(cls, *args, **kwargs):
        permission = getattr(cls, "permission", None)
        if permission is None:
            raise ImproperlyConfigured(
                "%s is missing the 'permission' attribute" % cls.__name__
            )
        return super().__new__(cls, *args, **kwargs)

    def _has_zaak_permission(self, request: Request, zaak_url: str):
        # retrieve the zaak to check permissions for
        try:
            zaak = get_zaak(zaak_url=zaak_url)
        except ClientError:
            logger.info("Invalid Zaak specified", exc_info=True)
            return False

        return request.user.has_perm(self.permission.name, zaak)

    def has_permission(self, request: Request, view: APIView) -> bool:
        serializer = view.get_serializer(data=request.data)
        # if the serializer is not valid, we want to see validation errors -> permission is granted
        if not serializer.is_valid():
            return True

        zaak_url = serializer.validated_data[self.zaak_attr]
        return self._has_zaak_permission(request, zaak_url)
