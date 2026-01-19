import logging
from typing import Dict, Union

from django.http import Http404
from django.utils.translation import gettext_lazy as _

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from zac.api.permissions import DefinitionBasePermission, ZaakDefinitionPermission
from zac.core.services import find_zaak
from zgw.models.zrc import Zaak

from ..models import ChecklistLock
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


class ChecklistIsLockedByCurrentUser(BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        if request.user.is_superuser:
            return True
        try:
            checklist_object = view.get_checklist_object()
        except (
            Http404
        ):  # Allow user to create a checklist or return a 404 message instead of 403.
            return True
        return self.has_object_permission(request, view, checklist_object)

    def has_object_permission(
        self, request: Request, view: APIView, obj: Union[Zaak, Dict]
    ) -> bool:
        if request.user.is_superuser:
            return True

        if isinstance(obj, Zaak):
            try:
                obj = view.get_checklist_object()
            except (
                Http404
            ):  # Allow user to create a checklist or return a 404 message instead of 403.
                return True

        if request.method in [
            "PUT",
            "POST",
        ]:  # At (un)lock and put we need to make sure only the locker has permissions
            # if lock is attempted, the lock will bounce if it's not the same locker. it's harmless to call lock an extra time.
            # if unlock is attempted the unlock will bounce if it's not the same locker. an unlock on an unlocked resource is harmless
            # if put is attempted the put will only be successful if the resource is locked by the updater
            if obj["record"]["data"]["locked"]:
                self.message = _(
                    "Checklist has been locked because the ZAAK is closed."
                )
                return False

            checklist_lock = ChecklistLock.objects.filter(url=obj["url"])
            if checklist_lock.exists():
                self.message = f"{checklist_lock[0]}"
                return checklist_lock.get().user == request.user

            # if put is attempted but there is no username the resource wasn't locked - return 403
            if request.method == "PUT" and not checklist_lock.exists():
                self.message = _(
                    "Checklist needs to be locked before you can update it."
                )
                return False
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
