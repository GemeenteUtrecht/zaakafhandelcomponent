import logging

from rest_framework.permissions import IsAdminUser
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from zac.api.permissions import DefinitionBasePermission, ZaakDefinitionPermission
from zgw.models.zrc import Zaak

from ..models import Checklist
from ..permissions import checklists_inzien, checklists_schrijven, checklisttypes_inzien

logger = logging.getLogger(__name__)


class CanReadOrWriteChecklistsPermission(ZaakDefinitionPermission):
    def get_permission(self, request):
        if request.method == "GET":
            return checklists_inzien
        return checklists_schrijven

    def has_permission(self, request: Request, view: ModelViewSet):
        if request.method != "GET":
            return super().has_permission(request, view)

        if request.user.is_superuser:
            return True

        # user should have permissions for zaak in query params
        zaak_url = request.query_params.get("zaak")
        if not zaak_url:
            return True

        zaak = self.get_object(request, zaak_url)
        if not zaak:
            return False
        return self.has_object_permission(request, view, zaak)

    def has_object_permission(self, request: Request, view: ModelViewSet, obj):
        zaak = self.get_object(request, obj.zaak) if isinstance(obj, Checklist) else obj

        return super().has_object_permission(request, view, zaak)


class CanReadZaakChecklistTypePermission(ZaakDefinitionPermission):
    permission = checklisttypes_inzien

    def has_permission(self, request: Request, view: ModelViewSet):
        if request.method != "GET":
            return super().has_permission(request, view)

        if request.user.is_superuser:
            return True

        # user should have permissions for zaak in query params
        zaak_url = request.query_params.get("zaak")
        if not zaak_url:
            return True

        zaak = self.get_object(request, zaak_url)
        if not zaak:
            return False
        return self.has_object_permission(request, view, zaak)

    def has_object_permission(self, request: Request, view: ModelViewSet, obj):
        if isinstance(obj, Zaak):
            return super().has_object_permission(request, view, obj)
        return False


class CanReadOrWriteChecklistTypePermission:
    def get_permission(self, request, view: APIView) -> DefinitionBasePermission:
        if view.action == "list":
            return CanReadZaakChecklistTypePermission()
        if (
            view.action == "retrieve"
            or view.action == "create"
            or view.action == "update"
        ):
            return IsAdminUser()

    def has_permission(self, request: Request, view: APIView) -> bool:
        permission = self.get_permission(request, view)
        return permission.has_permission(request, view)

    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        permission = self.get_permission(request, view)
        return permission.has_object_permission(request, view, obj)
