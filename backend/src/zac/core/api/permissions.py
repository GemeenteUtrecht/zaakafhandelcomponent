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

    def has_permission(self, request: Request, view: APIView) -> bool:
        if request.method not in permissions.SAFE_METHODS:
            return False
        return super().has_permission(request, view)


class CanHandleAccessRequests(RulesPermission):
    permission = zaken_handle_access
