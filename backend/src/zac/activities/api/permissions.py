import logging

from rest_framework.request import Request
from rest_framework.viewsets import ModelViewSet

from zac.api.permissions import ZaakDefinitionPermission
from zac.core.api.permissions import CanForceEditClosedZaak, CanForceEditClosedZaken

from ..models import Activity
from ..permissions import activiteiten_inzien, activiteiten_schrijven

logger = logging.getLogger(__name__)


class CanReadOrWriteActivitiesPermission(ZaakDefinitionPermission):
    def get_permission(self, request):
        if request.method == "GET":
            return activiteiten_inzien
        return activiteiten_schrijven

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
        zaak = self.get_object(request, obj.zaak) if isinstance(obj, Activity) else obj

        return super().has_object_permission(request, view, zaak)


class CanForceWriteActivitiesPermission(CanForceEditClosedZaken):
    def has_object_permission(self, request: Request, view: ModelViewSet, obj):
        zaak = self.get_object(request, obj.zaak) if isinstance(obj, Activity) else obj
        return super().has_object_permission(request, view, zaak)


class CanWriteEventsPermission(ZaakDefinitionPermission):
    object_attr = "activity"
    permission = activiteiten_schrijven

    def has_permission(self, request: Request, view: ModelViewSet):
        if view.action not in ("create",):
            return False

        return super().has_permission(request, view)

    def has_object_permission(self, request: Request, view: ModelViewSet, obj):
        if view.action not in ("create",):
            return False

        return super().has_object_permission(request, view, obj)

    def get_object_url(self, serializer):
        activity = super().get_object_url(serializer)
        return activity.zaak


class CanForceWriteEventsPermission(CanForceEditClosedZaak):
    object_attr = "activity"

    def get_object_url(self, serializer):
        activity = super().get_object_url(serializer)
        return activity.zaak
