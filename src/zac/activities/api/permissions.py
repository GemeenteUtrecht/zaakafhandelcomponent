from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.viewsets import ModelViewSet

from zac.core.services import get_zaak


class CanReadZaakPermission(permissions.IsAuthenticated):
    def has_object_permission(self, request: Request, view: ModelViewSet, obj):
        zaak = get_zaak(zaak_url=obj.zaak)
        return request.user.has_perm("activities:read", zaak)
