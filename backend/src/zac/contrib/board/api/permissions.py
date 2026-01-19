from zac.accounts.permissions import Permission
from zac.api.permissions import DefinitionBasePermission, ZaakDefinitionPermission
from zac.core.api.permissions import CanForceEditClosedZaak
from zac.core.permissions import zaken_inzien

from ..models import BoardItem

management_dashboard_inzien = Permission(
    name="management-dashboard:inzien",
    description="Laat toe om management dashboard in te zien.",
)


class CanUseBoardItem(ZaakDefinitionPermission):
    permission = zaken_inzien

    def get_object_url(self, serializer) -> str:
        return serializer.validated_data["object"]

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, BoardItem):
            obj = self.get_object(request, obj.object)
        return super().has_object_permission(request, view, obj)


class CanForceUseBoardItem(CanForceEditClosedZaak):
    def get_object_url(self, serializer) -> str:
        return serializer.validated_data["object"]

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, BoardItem):
            obj = self.get_object(request, obj.object)
        return super().has_object_permission(request, view, obj)


class CanReadManagementDashboard(DefinitionBasePermission):
    permission = management_dashboard_inzien
