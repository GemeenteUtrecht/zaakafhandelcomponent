import logging

from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.viewsets import ModelViewSet
from zds_client import ClientError

from zac.core.services import get_zaak

from ..models import Activity, Event
from ..permissions import activiteiten_schrijven

logger = logging.getLogger(__name__)


class CanReadZaakPermission(permissions.BasePermission):
    def has_permission(self, request: Request, view: ModelViewSet):
        return request.method == "GET"

    def has_object_permission(self, request: Request, view: ModelViewSet, obj):
        zaak = get_zaak(zaak_url=obj.zaak)
        return request.user.has_perm("activities:read", zaak)


class CanWritePermission(permissions.BasePermission):
    def has_permission(self, request: Request, view: ModelViewSet):
        if view.action not in ("create", "update", "partial_update"):
            return False

        serializer = view.get_serializer(data=request.data)
        # if the serializer is not valid, we want to see validation errors -> permission is granted
        if not serializer.is_valid():
            return True

        # determine the relevant zaak
        if view.queryset.model is Activity:
            zaak_url = serializer.validated_data["zaak"]
        elif view.queryset.model is Event:
            zaak_url = serializer.validated_data["activity"].zaak
        else:
            raise ValueError("Unknown model/queryset")

        # retrieve the zaak to check permissions for
        try:
            zaak = get_zaak(zaak_url=zaak_url)
        except ClientError:
            logger.info("Invalid Zaak specified", exc_info=True)
            return False

        return request.user.has_perm(activiteiten_schrijven.name, zaak)

    def has_object_permission(self, request: Request, view: ModelViewSet, obj):
        return False
