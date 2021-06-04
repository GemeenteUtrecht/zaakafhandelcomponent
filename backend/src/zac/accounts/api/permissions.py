import logging

from rest_framework.request import Request
from rest_framework.views import APIView
from zds_client import ClientError

from zac.api.permissions import DefinitionBasePermission, ZaakDefinitionPermission
from zac.core.permissions import zaken_handle_access, zaken_request_access
from zac.core.services import get_zaak

from ..models import AccessRequest

logger = logging.getLogger(__name__)


class CanGrantAccess(ZaakDefinitionPermission):
    object_attr = "object_url"
    permission = zaken_handle_access


class CanRequestAccess(ZaakDefinitionPermission):
    permission = zaken_request_access


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
