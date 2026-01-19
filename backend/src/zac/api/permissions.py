import logging
from typing import Optional

from django.db.models import QuerySet

from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView
from zds_client import ClientError

from zac.accounts.constants import PermissionObjectTypeChoices
from zac.accounts.models import BlueprintPermission, UserAtomicPermission
from zac.core.permissions import Permission
from zac.core.services import get_document, get_informatieobjecttype, get_zaak

logger = logging.getLogger(__name__)


class DefinitionBasePermission(permissions.BasePermission):
    permission: Permission
    object_type: str = PermissionObjectTypeChoices.zaak

    def get_permission(self, request):
        assert self.permission is not None, (
            "'%s' should either include a `permission` attribute, "
            "or override the `get_permission()` method." % self.__class__.__name__
        )

        return self.permission

    def get_blueprint_permissions(self, request, permission_name) -> QuerySet:
        return BlueprintPermission.objects.for_requester(request, actual=True).filter(
            role__permissions__contains=[permission_name],
            object_type=self.object_type,
        )

    def user_atomic_permissions_exists(
        self, request, permission_name, obj_url: Optional[str] = ""
    ) -> bool:
        filters = {
            "user": request.user,
            "atomic_permission__permission": permission_name,
        }
        if obj_url:
            filters["atomic_permission__object_url"] = obj_url
        else:
            filters["atomic_permission__object_type"] = self.object_type

        return (
            UserAtomicPermission.objects.select_related("atomic_permission")
            .filter(**filters)
            .actual()
            .exists()
        )

    def has_object_permission(self, request: Request, view: APIView, obj):
        if request.user.is_superuser:
            return True

        permission_name = self.get_permission(request).name
        # first check atomic permissions - this checks both atomic permissions directly attached to the user
        # and atomic permissions defined to authorization profiles
        if self.user_atomic_permissions_exists(
            request, permission_name, obj_url=obj.url
        ):
            return True

        # then check blueprint permissions
        for permission in self.get_blueprint_permissions(request, permission_name):
            if permission.has_access(obj, request.user, permission_name):
                return True

        return False

    def has_permission(self, request: Request, view: APIView) -> bool:
        if request.user.is_superuser:
            return True

        permission_name = self.get_permission(request).name
        # check if the user has permissions for any object
        if (not self.get_blueprint_permissions(request, permission_name).exists()) and (
            not self.user_atomic_permissions_exists(request, permission_name)
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


class DocumentDefinitionPermission(ObjectDefinitionBasePermission):
    object_attr = "url"
    object_type = PermissionObjectTypeChoices.document

    def get_object(self, request: Request, obj_url: str):
        try:
            document = get_document(obj_url)
            document.informatieobjecttype = get_informatieobjecttype(
                document.informatieobjecttype
            )
        except ClientError:
            logger.info("Invalid Document specified", exc_info=True)
            return None

        return document
