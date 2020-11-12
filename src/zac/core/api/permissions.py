import logging

from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView
from zds_client import ClientError

from ..permissions import zaken_add_documents, zaken_add_relations
from ..services import get_zaak

logger = logging.getLogger(__name__)


class CanAddDocuments(permissions.BasePermission):
    def _has_zaak_permission(self, request: Request, zaak_url: str):
        # retrieve the zaak to check permissions for
        try:
            zaak = get_zaak(zaak_url=zaak_url)
        except ClientError:
            logger.info("Invalid Zaak specified", exc_info=True)
            return False

        return request.user.has_perm(zaken_add_documents.name, zaak)

    def has_permission(self, request: Request, view: APIView) -> bool:
        if request.method != "POST":
            return False

        serializer = view.get_serializer(data=request.data)
        # if the serializer is not valid, we want to see validation errors -> permission is granted
        if not serializer.is_valid():
            return True

        zaak_url = serializer.validated_data["zaak"]
        return self._has_zaak_permission(request, zaak_url)


class CanAddRelations(permissions.BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        if request.method != "POST":
            return False

        serializer = view.get_serializer(data=request.data)
        # if the serializer is not valid, we want to see validation errors -> permission is granted
        if not serializer.is_valid():
            return True

        # Check that the user has access to both zaken being related
        try:
            get_zaak(zaak_url=serializer.validated_data["main_zaak"])
            get_zaak(zaak_url=serializer.validated_data["relation_zaak"])
        except ClientError:
            logger.info("Invalid Zaak specified", exc_info=True)
            return False

        # Check that the user has permissions to add relations
        return request.user.has_perm(zaken_add_relations.name)
