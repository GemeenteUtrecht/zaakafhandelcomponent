import logging
from typing import Dict, Union

from django.http import Http404

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from zac.api.permissions import DefinitionBasePermission, ZaakDefinitionPermission
from zac.core.services import find_zaak
from zgw.models.zrc import Zaak

from ..permissions import checklists_inzien, checklists_schrijven, checklisttypes_inzien

logger = logging.getLogger(__name__)


class CanReadOrWriteChecklistsPermission(ZaakDefinitionPermission):
    def get_permission(self, request):
        if request.method == "GET":
            return checklists_inzien
        return checklists_schrijven

    def has_permission(self, request: Request, view: APIView) -> bool:
        if request.user.is_superuser:
            return True

        # user should have permissions for zaak in query params
        bronorganisatie = request.parser_context["kwargs"]["bronorganisatie"]
        identificatie = request.parser_context["kwargs"]["identificatie"]
        zaak = find_zaak(bronorganisatie, identificatie)
        if not zaak:
            return False
        return self.has_object_permission(request, view, zaak)


class ChecklistIsUnlockedOrLockedByCurrentUser(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        if request.user.is_superuser:
            return True
        try:
            checklist_object = view.get_checklist_object()
        except Http404:  # Allow user to create a checklist or return a 404 message instead of 403.
            return True
        return self.has_object_permission(request, view, checklist_object)

    def has_object_permission(
        self, request: Request, view: APIView, obj: Union[Zaak, Dict]
    ) -> bool:
        if request.user.is_superuser:
            return True

        if isinstance(obj, Zaak):
            obj = view.get_checklist_object()

        if username := obj["record"]["data"]["lockedBy"]:
            return request.user.username == username
        return True


class CanReadZaakChecklistTypePermission(DefinitionBasePermission):
    permission = checklisttypes_inzien

    def has_permission(self, request: Request, view: APIView) -> bool:
        if request.user.is_superuser or request.user.is_staff:
            return True

        # user should have permissions for zaak in path params
        bronorganisatie = request.parser_context["kwargs"]["bronorganisatie"]
        identificatie = request.parser_context["kwargs"]["identificatie"]
        zaak = find_zaak(bronorganisatie, identificatie)
        if not zaak:
            return False
        return self.has_object_permission(request, view, zaak)
