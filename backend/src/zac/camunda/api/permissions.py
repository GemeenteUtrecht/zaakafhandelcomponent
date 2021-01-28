from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView

from zac.core.permissions import zaakproces_usertasks

class CanPerformTasks(permissions.BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        if request.method not in permissions.SAFE_METHODS:
            return False
        return request.user.has_perm(zaakproces_usertasks.name)

    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        return request.user.has_perm(zaakproces_usertasks.name, obj)