import logging

from zac.api.permissions import ZaakDefinitionPermission
from zac.core.permissions import zaken_handle_access

logger = logging.getLogger(__name__)


class CanHandleAccess(ZaakDefinitionPermission):
    permission = zaken_handle_access
