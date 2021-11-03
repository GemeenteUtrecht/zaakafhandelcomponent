import logging
from dataclasses import dataclass

from rest_framework.request import Request
from rest_framework.views import APIView
from zds_client import ClientError

from zac.api.permissions import (
    DefinitionBasePermission,
    Permission,
    ZaakDefinitionPermission,
)
from zac.core.permissions import zaken_handle_access, zaken_request_access
from zac.core.services import get_zaak

from ..constants import PermissionObjectTypeChoices
from ..models import AccessRequest, UserAtomicPermission

logger = logging.getLogger(__name__)


class CanGrantAccess(ZaakDefinitionPermission):
    permission = zaken_handle_access

    def get_object_url(self, serializer) -> str:
        return serializer.validated_data["atomic_permission"]["object_url"]

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, UserAtomicPermission):
            obj = self.get_object(request, obj.atomic_permission.object_url)
        return super().has_object_permission(request, view, obj)

    def get_object(self, request: Request, obj_url: str):
        try:
            zaak = get_zaak(zaak_url=obj_url)
        except ClientError:
            logger.info("Invalid Zaak specified", exc_info=True)
            return None
        return zaak


class CanRequestAccess(ZaakDefinitionPermission):
    permission = zaken_request_access

    def get_object_url(self, serializer) -> str:
        return serializer.validated_data["zaak"].url


class CanHandleAccessRequest(DefinitionBasePermission):
    permission = zaken_handle_access

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, AccessRequest):
            obj = self.get_object(request, obj.zaak)
        return super().has_object_permission(request, view, obj)

    def get_object(self, request: Request, obj_url: str):
        try:
            zaak = get_zaak(zaak_url=obj_url)
        except ClientError:
            logger.info("Invalid Zaak specified", exc_info=True)
            return None
        return zaak


class CanCreateOrHandleAccessRequest:
    def get_permission(self, request) -> DefinitionBasePermission:
        if request.method == "POST":
            return CanRequestAccess()
        else:
            return CanHandleAccessRequest()

    def has_permission(self, request: Request, view: APIView) -> bool:
        permission = self.get_permission(request)
        return permission.has_permission(request, view)

    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        permission = self.get_permission(request)
        return permission.has_object_permission(request, view, obj)


@dataclass(frozen=True)
class GroupPermission(Permission):
    object_type: str = PermissionObjectTypeChoices.group


groep_beheren = GroupPermission(
    name="accounts:groep-beheren",
    description="Laat toe om groepen te beheren.",
)

groep_inzien = GroupPermission(
    name="accounts:groep-inzien",
    description="Laat toe om groepen in te zien.",
)


class GroupPermissionMixin:
    object_type: str = PermissionObjectTypeChoices.group

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
            qs = queryset.filter(**{view.lookup_field: view.kwargs[lookup_url_kwarg]})[
                0
            ]
        except IndexError:
            logger.info(
                "%s with %s %s does not exist"
                % (self.object_type, view.lookup_field, view.kwargs[lookup_url_kwarg]),
                exc_info=True,
            )
            return None
        return qs


class CanChangeGroup(GroupPermissionMixin, DefinitionBasePermission):
    permission = groep_beheren


class CanViewGroup(GroupPermissionMixin, DefinitionBasePermission):
    permission = groep_inzien


class ManageGroup:
    def get_permission(self, request) -> DefinitionBasePermission:
        if request.method == "GET":
            return CanViewGroup()
        else:
            return CanChangeGroup()

    def has_permission(self, request: Request, view: APIView) -> bool:
        return self.get_permission(request).has_permission(request, view)

    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        return self.get_permission(request).has_object_permission(request, view, obj)
