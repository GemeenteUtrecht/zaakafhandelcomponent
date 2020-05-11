import logging
from typing import Optional, Union

import rules
from zgw_consumers.api_models.zaken import Zaak

from zac.accounts.models import User
from zac.accounts.permissions import Permission, register

from .permissions import (
    zaakproces_send_message,
    zaakproces_usertasks,
    zaken_close,
    zaken_inzien,
    zaken_set_result,
)

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


@register(
    zaken_inzien,
    zaakproces_send_message,
    zaakproces_usertasks,
    zaken_set_result,
    zaken_close,
)
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


def _has_permission_key(permission_name: str, user: User):
    available_perms = user._zaaktype_perms._permissions.keys()
    return permission_name in available_perms


@rules.predicate
def can_close_zaken(user: User, zaak: Optional[Zaak]):
    if zaak is None:
        return _has_permission_key(zaken_close.name, user)
    if zaak.einddatum:
        return False
    return _generic_zaakpermission(user, zaak, zaken_close)


@rules.predicate
def can_set_results(user: User, zaak: Optional[Zaak]):
    if zaak is None:
        return _has_permission_key(zaken_set_result.name, user)
    if zaak.einddatum:
        return False
    return _generic_zaakpermission(user, zaak, zaken_set_result)


rules.add_rule("zaken:afhandelen", can_close_zaken | can_set_results)
