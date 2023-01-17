import logging

from rest_framework.request import Request
from rest_framework.viewsets import ModelViewSet

from zac.api.permissions import DefinitionBasePermission, ZaakDefinitionPermission
from zac.core.services import find_zaak

from ..permissions import checklists_inzien, checklists_schrijven, checklisttypes_inzien

logger = logging.getLogger(__name__)


class CanReadOrWriteChecklistsPermission(ZaakDefinitionPermission):
    def get_permission(self, request):
        if request.method == "GET":
            return checklists_inzien
        return checklists_schrijven

    def has_permission(self, request: Request, view: ModelViewSet):
        if request.user.is_superuser:
            return True

        # user should have permissions for zaak in query params
        bronorganisatie = request.parser_context["kwargs"]["bronorganisatie"]
        identificatie = request.parser_context["kwargs"]["identificatie"]
        zaak = find_zaak(bronorganisatie, identificatie)
        if not zaak:
            return False
        return self.has_object_permission(request, view, zaak)


class CanReadZaakChecklistTypePermission(DefinitionBasePermission):
    permission = checklisttypes_inzien

    def has_permission(self, request: Request, view: ModelViewSet):
        if request.user.is_superuser or request.user.is_staff:
            return True

        # user should have permissions for zaak in path params
        bronorganisatie = request.parser_context["kwargs"]["bronorganisatie"]
        identificatie = request.parser_context["kwargs"]["identificatie"]
        zaak = find_zaak(bronorganisatie, identificatie)
        if not zaak:
            return False
        return self.has_object_permission(request, view, zaak)
