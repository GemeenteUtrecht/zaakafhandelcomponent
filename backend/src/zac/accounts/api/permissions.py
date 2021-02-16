import logging

from zac.api.permissions import ZaakBasedPermission
from zac.core.rules import zaken_handle_access

logger = logging.getLogger(__name__)


class CanHandleAccess(ZaakBasedPermission):
    permission = zaken_handle_access
