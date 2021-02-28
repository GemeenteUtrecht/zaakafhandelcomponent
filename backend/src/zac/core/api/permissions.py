import logging

from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView

from zac.api.permissions import RulesPermission, ZaakBasedPermission

from ..permissions import (
    zaken_add_documents,
    zaken_add_relations,
    zaken_handle_access,
    zaken_inzien,
    zaken_wijzigen,
)

logger = logging.getLogger(__name__)


class CanAddDocuments(ZaakBasedPermission):
    permission = zaken_add_documents

    def has_permission(self, request: Request, view: APIView) -> bool:
        if request.method != "POST":
            return False

        return super().has_permission(request, view)


class CanAddRelations(ZaakBasedPermission):
    permission = zaken_add_relations
    zaak_attr = "main_zaak"

    def has_permission(self, request: Request, view: APIView) -> bool:
        if request.method != "POST":
            return False

        return super().has_permission(request, view)


class CanReadZaken(RulesPermission):
    permission = zaken_inzien


class CanUpdateZaken(RulesPermission):
    permission = zaken_wijzigen


class CanReadOrUpdateZaken:
    def get_permission(self, request) -> RulesPermission:
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


class CanHandleAccessRequests(RulesPermission):
    permission = zaken_handle_access
