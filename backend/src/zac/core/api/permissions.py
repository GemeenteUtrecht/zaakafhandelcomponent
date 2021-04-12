import logging

from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView

from zac.api.permissions import DefinitionBasePermission, ZaakDefinitionPermission

from ..permissions import (
    zaken_add_documents,
    zaken_add_relations,
    zaken_download_documents,
    zaken_handle_access,
    zaken_inzien,
    zaken_update_documents,
    zaken_wijzigen,
)
from ..services import get_documenten

logger = logging.getLogger(__name__)


class CanAddDocuments(ZaakDefinitionPermission):
    permission = zaken_add_documents

    def has_permission(self, request: Request, view: APIView) -> bool:
        if request.method != "POST":
            return False

        return super().has_permission(request, view)


class CanAddRelations(ZaakDefinitionPermission):
    permission = zaken_add_relations
    object_attr = "main_zaak"

    def has_permission(self, request: Request, view: APIView) -> bool:
        if request.method != "POST":
            return False

        return super().has_permission(request, view)


class CanReadZaken(DefinitionBasePermission):
    permission = zaken_inzien


class CanUpdateZaken(DefinitionBasePermission):
    permission = zaken_wijzigen


class CanReadOrUpdateZaken:
    def get_permission(self, request) -> DefinitionBasePermission:
        if request.method in permissions.SAFE_METHODS:
            return CanReadZaken()
        else:
            return CanUpdateZaken()

    def has_permission(self, request: Request, view: APIView) -> bool:
        permission = self.get_permission(request)
        return permission.has_permission(request, view)

    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        permission = self.get_permission(request)
        return permission.has_object_permission(request, view, obj)


class CanHandleAccessRequests(DefinitionBasePermission):
    permission = zaken_handle_access
