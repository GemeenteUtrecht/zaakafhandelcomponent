from zac.accounts.constants import PermissionObjectType
from zac.api.permissions import DefinitionBasePermission
from zac.core.permissions import zaken_download_documents


class CanOpenDocuments(DefinitionBasePermission):
    permission = zaken_download_documents.name
    object_type = PermissionObjectType.document
