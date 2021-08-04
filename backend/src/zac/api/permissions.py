import logging

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

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True

        permission_name = self.get_permission(request).name
        # first check atomic permissions - this checks both atomic permissions directly attached to the user
        # and atomic permissions defined to authorization profiles
        if (
            UserAtomicPermission.objects.select_related("atomic_permission")
            .filter(
                user=request.user,
                atomic_permission__permission=permission_name,
                atomic_permission__object_url=obj.url,
            )
            .actual()
            .exists()
        ):
            return True

        # then check blueprint permissions
        for permission in (
            BlueprintPermission.objects.for_user(request.user)
            .filter(
                role__permissions__contains=[permission_name],
                object_type=self.object_type,
            )
            .actual()
        ):
            if permission.has_access(obj, request.user, permission_name):
                return True

        return False

    def has_permission(self, request: Request, view: APIView) -> bool:
        if request.user.is_superuser:
            return True

        permission_name = self.get_permission(request).name
        # check if the user has permissions for any object
        if (
            not BlueprintPermission.objects.for_user(request.user)
            .filter(
                role__permissions__contains=[permission_name],
                object_type=self.object_type,
            )
            .actual()
            .exists()
        ) and (
            not UserAtomicPermission.objects.select_related("atomic_permission")
            .filter(
                user=request.user,
                atomic_permission__permission=permission_name,
                atomic_permission__object_type=self.object_type,
            )
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


class SearchReportDefinitionPermission(DefinitionBasePermission):
    object_attr = "search_report"
    object_type: str = PermissionObjectTypeChoices.search_report

    def get_object(self, view):
        # Mostly taken from get_object_or_404 but without obj permission checks.
        queryset = view.filter_queryset(view.get_queryset())

        # Perform the lookup filtering.
        lookup_url_kwarg = view.lookup_url_kwarg or view.lookup_field

        assert lookup_url_kwarg in view.kwargs, (
            "Expected view %s to be called with a URL keyword argument "
            'named "%s". Fix your URL conf, or set the `.lookup_field` '
            "attribute on the view correctly."
            % (view.__class__.__name__, lookup_url_kwarg)
        )

        try:
            search_report = queryset.filter(
                **{view.lookup_field: view.kwargs[lookup_url_kwarg]}
            )[0]
        except IndexError:
            logger.info(
                "Search report with %s %s does not exist"
                % (view.lookup_field, view.kwargs[lookup_url_kwarg]),
                exc_info=True,
            )
            return None
        return search_report

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True

        # check blueprint permissions
        for permission in (
            BlueprintPermission.objects.for_user(request.user)
            .filter(
                role__permissions__contains=[self.permission.name],
                object_type=self.object_type,
            )
            .actual()
        ):
            if permission.has_access(obj, request.user, self.permission.name):
                return True

        return False

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

        obj = self.get_object(view)
        if not obj:
            return False
        return self.has_object_permission(request, view, obj)


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
