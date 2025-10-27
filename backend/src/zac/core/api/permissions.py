import logging

from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView

from zac.accounts.constants import PermissionObjectTypeChoices
from zac.api.permissions import (
    DefinitionBasePermission,
    DocumentDefinitionPermission,
    ZaakDefinitionPermission,
)
from zgw.models import Zaak

from ..permissions import (
    zaken_aanmaken,
    zaken_add_documents,
    zaken_add_relations,
    zaken_download_documents,
    zaken_geforceerd_bijwerken,
    zaken_handle_access,
    zaken_inzien,
    zaken_list_documents,
    zaken_update_documents,
    zaken_wijzigen,
)

logger = logging.getLogger(__name__)


class BaseConditionalPermission:
    def get_permission(self, request: Request):
        raise NotImplementedError("This method must be implemented by a subclass")

    def has_permission(self, request: Request, view: APIView) -> bool:
        permission = self.get_permission(request)
        return permission.has_permission(request, view)

    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        permission = self.get_permission(request)
        return permission.has_object_permission(request, view, obj)


###############################
#            Zaken            #
###############################


class CanForceEditClosedZaak(ZaakDefinitionPermission):
    permission = zaken_geforceerd_bijwerken

    def check_for_any_permission(self, request, obj) -> bool:
        if request.user.is_superuser:
            return True

        atomic_permission_for_obj = self.user_atomic_permissions_exists(
            request, zaken_geforceerd_bijwerken.name, obj_url=obj.url
        )
        atomic_permission_for_obj_type = self.user_atomic_permissions_exists(
            request, zaken_geforceerd_bijwerken.name
        )
        blueprint_permission = self.get_blueprint_permissions(
            request, zaken_geforceerd_bijwerken.name
        ).exists()
        return (
            atomic_permission_for_obj
            or atomic_permission_for_obj_type
            or blueprint_permission
        )

    def has_permission(self, request: Request, view: APIView) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True

        serializer = view.get_serializer(data=request.data)
        # if the serializer is not valid, we want to see validation errors -> permission is granted
        if not serializer.is_valid():
            return True

        try:
            object_url = self.get_object_url(serializer)
            obj = self.get_object(request, object_url)
        except (
            KeyError
        ):  # could be that a permission check is done on one of the /<bronorganisatie>/<identificatie>/-urls. in that case, try to fetch object from view directly
            obj = view.get_object()
            if not isinstance(obj, Zaak):
                return False

        if not obj:
            return False
        return self.has_object_permission(request, view, obj)

    def has_object_permission(self, request: Request, view: APIView, obj) -> bool:
        if request.method in permissions.SAFE_METHODS:
            return True

        # Check if zaak is closed or open.
        # if it's closed - check for force edit permissions.
        if obj.einddatum is not None:
            return self.check_for_any_permission(request, obj)
        return True


class CanForceEditClosedZaken(CanForceEditClosedZaak):
    def has_permission(self, *args):
        # The initial request will be allowed. Object permissions must be checked.
        return True


class CanAddRelations(ZaakDefinitionPermission):
    permission = zaken_add_relations
    object_attr = "hoofdzaak"


class CanAddReverseRelations(ZaakDefinitionPermission):
    permission = zaken_add_relations
    object_attr = "bijdragezaak"


class CanForceAddRelations(CanForceEditClosedZaak):
    object_attr = "hoofdzaak"


class CanForceAddReverseRelations(CanForceEditClosedZaak):
    object_attr = "bijdragezaak"


class CanReadZaken(DefinitionBasePermission):
    permission = zaken_inzien


class CanListZaakDocuments(DefinitionBasePermission):
    permission = zaken_list_documents


class CanUpdateZaken(DefinitionBasePermission):
    permission = zaken_wijzigen


class CanReadOrUpdateZaken(BaseConditionalPermission):
    def get_permission(self, request) -> DefinitionBasePermission:
        if request.method in permissions.SAFE_METHODS:
            return CanReadZaken()
        else:
            return CanUpdateZaken()


class CanCreateZaken(DefinitionBasePermission):
    permission = zaken_aanmaken


###############################
#          Documents          #
###############################


class CanReadDocuments(DefinitionBasePermission):
    permission = zaken_download_documents
    object_type = PermissionObjectTypeChoices.document


class CanAddDocuments(ZaakDefinitionPermission):
    permission = zaken_add_documents


class CanUpdateDocuments(DocumentDefinitionPermission):
    permission = zaken_update_documents


class CanAddOrUpdateZaakDocuments(BaseConditionalPermission):
    def get_permission(self, request) -> DefinitionBasePermission:
        if request.method == "PATCH":
            return CanUpdateDocuments()
        elif request.method == "POST":
            return CanAddDocuments()


###############################
#       Access Requests       #
###############################


class CanHandleAccessRequests(DefinitionBasePermission):
    permission = zaken_handle_access
