import logging
from typing import Union

from zgw_consumers.api_models.zaken import Zaak

from zac.accounts.permissions import Permission, register

from .permissions import zaakproces_send_message, zaakproces_usertasks, zaken_inzien

logger = logging.getLogger(__name__)


class dictwrapper:
    def __init__(self, obj):
        self._obj = obj

    def __repr__(self):
        return repr(self._obj)

    def __getattr__(self, attr: str):
        if hasattr(self._obj, attr):
            return getattr(self._obj, attr)

        if attr in self._obj:
            return self._obj[attr]

        raise AttributeError(f"Obj {self._obj} has no attribute '{attr}'")


@register(zaken_inzien, zaakproces_send_message, zaakproces_usertasks)
def _generic_zaakpermission(user, zaak: Union[dict, Zaak], permission: Permission):
    logger.debug("Checking permission %r for user %r", permission, user)
    zaak = dictwrapper(zaak)

    zaaktype_url = zaak.zaaktype
    if not isinstance(zaaktype_url, str):
        zaaktype_url = zaaktype_url.url

    permissions = user._zaaktype_perms
    return permissions.contains(
        permission=permission.name,
        zaaktype=zaaktype_url,
        vertrouwelijkheidaanduiding=zaak.vertrouwelijkheidaanduiding,
    )
