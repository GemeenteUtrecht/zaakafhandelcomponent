import logging

from django.core.exceptions import ImproperlyConfigured

from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView
from zds_client import ClientError

from zac.accounts.constants import PermissionObjectType
from zac.accounts.models import AtomicPermission, BlueprintPermission
from zac.core.permissions import Permission
from zac.core.services import get_zaak

logger = logging.getLogger(__name__)


class DefinitionBasePermission(permissions.BasePermission):
    permission: Permission
    object_type: str = PermissionObjectType.zaak

    def get_permission(self, request):
        assert self.permission is not None, (
            "'%s' should either include a `permission` attribute, "
            "or override the `get_permission()` method." % self.__class__.__name__
        )

        return self.permission

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True

        permission_name = self.get_permission(request).name
        # first check atomic permissions - this checks both atomic permissions directly attached to the user
        # and atomic permissions defined to authorization profiles
        if (
            AtomicPermission.objects.for_user(request.user)
            .filter(permission=permission_name, object_url=obj.url)
            .actual()
            .exists()
        ):
            return True

        # then check blueprint permissions
        for permission in (
            BlueprintPermission.objects.for_user(request.user)
            .filter(permission=permission_name, object_type=self.object_type)
            .actual()
        ):
            if permission.has_access(obj, request.user):
                return True

        return False

    def has_permission(self, request: Request, view: APIView) -> bool:
        if request.user.is_superuser:
            return True

        permission_name = self.get_permission(request).name
        # check if the user has permissions for any object
        if (
            not BlueprintPermission.objects.for_user(request.user)
            .filter(permission=permission_name, object_type=self.object_type)
            .actual()
            .exists()
        ) and (
            not AtomicPermission.objects.for_user(request.user)
            .filter(permission=permission_name, object_type=self.object_type)
            .actual()
            .exists()
        ):
            return False

        return super().has_permission(request, view)


class ObjectDefinitionBasePermission(DefinitionBasePermission):
    object_attr: str

    def get_object(self, request: Request, obj_url: str):
        raise NotImplementedError("This method must be implemented by a subclass")

    def get_object_url(self, serializer) -> str:
        return serializer.validated_data[self.object_attr]

    def has_permission(self, request: Request, view: APIView) -> bool:
        if request.user.is_superuser:
            return True

        serializer = view.get_serializer(data=request.data)
        # if the serializer is not valid, we want to see validation errors -> permission is granted
        if not serializer.is_valid():
            return True

        # first check  if the user has permissions for any object
        if not super().has_permission(request, view):
            return False

        object_url = self.get_object_url(serializer)
        obj = self.get_object(request, object_url)
        if not obj:
            return False
        return self.has_object_permission(request, view, obj)


class ZaakDefinitionPermission(ObjectDefinitionBasePermission):
    object_attr = "zaak"

    def get_object(self, request: Request, obj_url: str):
        try:
            zaak = get_zaak(zaak_url=obj_url)
        except ClientError:
            logger.info("Invalid Zaak specified", exc_info=True)
            return None

        return zaak
