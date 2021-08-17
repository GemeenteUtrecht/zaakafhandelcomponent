from zac.accounts.constants import PermissionObjectTypeChoices
from zac.api.permissions import DefinitionBasePermission
from zac.core.permissions import zaken_download_documents


class CanOpenDocuments(DefinitionBasePermission):
    permission = zaken_download_documents
    object_type = PermissionObjectTypeChoices.document
