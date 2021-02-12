import logging

from rest_framework.request import Request
from rest_framework.views import APIView

from zac.api.permissions import ZaakBasedPermission
from zac.core.rules import zaken_handle_access

logger = logging.getLogger(__name__)


class CanHandleAccess(ZaakBasedPermission):
    permission = zaken_handle_access

    def has_permission(self, request: Request, view: APIView) -> bool:
        if request.method != "POST":
            return False

        return super().has_permission(request, view)
