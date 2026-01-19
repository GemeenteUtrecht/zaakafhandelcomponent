from rest_framework.request import Request
from rest_framework.views import APIView

from zac.api.permissions import DefinitionBasePermission
from zac.core.permissions import zaakprocess_starten


class CanStartCamundaProcess(DefinitionBasePermission):
    permission = zaakprocess_starten

    def has_permission(self, request: Request, view: APIView) -> bool:
        # first check  if the user has permissions for any object
        if not super().has_permission(request, view):
            return False

        obj = view.get_object()
        if not obj:
            return False
        return self.has_object_permission(request, view, obj)
