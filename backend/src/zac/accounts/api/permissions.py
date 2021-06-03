import logging

from zac.api.permissions import ZaakDefinitionPermission
from zac.core.permissions import zaken_handle_access, zaken_request_access

logger = logging.getLogger(__name__)


class CanHandleAccess(ZaakDefinitionPermission):
    object_attr = "object_url"
    permission = zaken_handle_access


class CanRequestAccess(ZaakDefinitionPermission):
    permission = zaken_request_access
