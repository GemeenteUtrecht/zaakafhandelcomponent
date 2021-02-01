from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView

from zac.api.permissions import RulesPermission
from zac.core.permissions import zaakproces_send_message, zaakproces_usertasks


class CanPerformTasks(RulesPermission):
    """
    TODO: Write tests.
    """

    permission = zaakproces_usertasks

    def has_permission(self, request: Request, view: APIView) -> bool:
        if request.method not in permissions.SAFE_METHODS:
            return False
        return super().has_permission(request, view)


class CanSendMessages(RulesPermission):
    permission = zaakproces_send_message
