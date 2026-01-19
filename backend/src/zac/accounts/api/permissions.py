import logging

from django.contrib.auth.models import Group

from rest_framework import serializers
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView
from zds_client import ClientError

from zac.api.permissions import DefinitionBasePermission, ZaakDefinitionPermission
from zac.core.api.permissions import CanForceEditClosedZaak, CanForceEditClosedZaken
from zac.core.permissions import zaken_handle_access
from zac.core.services import get_zaak

from ..models import AccessRequest, ApplicationToken, UserAtomicPermission
from ..utils import permissions_related_to_user

logger = logging.getLogger(__name__)


###############################
#       Access Requests       #
###############################


class GrantAccessMixin:
    def get_object_url(self, serializer) -> str:
        if isinstance(serializer, serializers.ListSerializer):
            # Do not allow a mix of object_urls at this point.
            # Only one object can be granted multiple atomic
            # permissions in the same request.
            objects = {
                child_serializer["atomic_permission"]["object_url"]
                for child_serializer in serializer.validated_data
            }
            if len(objects) > 1:
                return False
            return serializer.validated_data[0]["atomic_permission"]["object_url"]
        return serializer.validated_data["atomic_permission"]["object_url"]

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, UserAtomicPermission):
            allowed_perms = permissions_related_to_user(request)
            if obj.atomic_permission.permission not in [
                perm.name for perm in allowed_perms
            ]:
                return False

            obj = self.get_object(request, obj.atomic_permission.object_url)
        return super().has_object_permission(request, view, obj)

    def get_object(self, request: Request, obj_url: str):
        try:
            zaak = get_zaak(zaak_url=obj_url)
        except ClientError:
            logger.info("Invalid Zaak specified", exc_info=True)
            return None
        return zaak


class CanGrantAccess(GrantAccessMixin, ZaakDefinitionPermission):
    permission = zaken_handle_access


class CanForceGrantAccess(GrantAccessMixin, CanForceEditClosedZaak):
    pass


class RequestMixin:
    def get_object_url(self, serializer) -> str:
        return serializer.validated_data["zaak"].url


class HandleAccessRequestMixin:
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


class CanCreateOrHandleAccessRequest(
    HandleAccessRequestMixin, DefinitionBasePermission
):
    permission = zaken_handle_access

    def has_permission(self, request: Request, view: APIView) -> bool:
        if request.method == "POST":
            return True
        return super().has_permission(request, view)

    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        if request.method == "POST":
            return True
        return super().has_object_permission(request, view, obj)


class CanForceCreateOrHandleAccessRequest(
    HandleAccessRequestMixin, CanForceEditClosedZaken
):
    def has_permission(self, request: Request, view: APIView) -> bool:
        if request.method == "POST":
            return True
        return super().has_permission(request, view)

    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        if request.method == "POST":
            return True
        return super().has_object_permission(request, view, obj)


###############################
#           Groups            #
###############################


class GroupBasePermission:
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
                "Group with %s %s does not exist"
                % (self.object_type, view.lookup_field, view.kwargs[lookup_url_kwarg]),
                exc_info=True,
            )
            return None
        return qs

    def has_permission(self, request: Request, view: APIView):
        if request.user.is_superuser:
            return True

        if view.action == "create":
            return True

        obj = self.get_object(view)
        return self.has_object_permission(request, view, obj)


class CanChangeGroup(GroupBasePermission):
    def has_object_permission(self, request: Request, view: APIView, obj: Group):
        if request.user.is_superuser:
            return True
        return obj in request.user.manages_groups.all()


class CanViewGroup(GroupBasePermission):
    def has_object_permission(self, request: Request, view: APIView, obj: Group):
        if request.user.is_superuser:
            return True
        return (
            request.user in obj.user_set.all()
            or obj in request.user.manages_groups.all()
        )


class ManageGroup:
    def get_permission(self, request) -> DefinitionBasePermission:
        if request.method == "GET":
            return CanViewGroup()
        else:
            return CanChangeGroup()

    def has_permission(self, request: Request, view: APIView) -> bool:
        if request.method == "GET":
            if view.action == "list":
                return True
        return self.get_permission(request).has_permission(request, view)

    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        return self.get_permission(request).has_object_permission(request, view, obj)


###############################
#   Application Permissions   #
###############################


class HasTokenAuth(BasePermission):
    def has_permission(self, request, view) -> bool:
        if request.auth and isinstance(request.auth, ApplicationToken):
            return True
        return False
