from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.views import APIView

from zac.core.permissions import zaken_download_documents


class CanOpenDocuments(permissions.BasePermission):
    def has_permission(self, request: Request, view: APIView) -> bool:
        return request.user.has_perm(zaken_download_documents.name)
