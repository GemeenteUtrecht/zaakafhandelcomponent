import rules

from zac.accounts.models import User
from zac.accounts.permissions import register
from zac.core.permissions import zaken_inzien
from zac.core.rules import _generic_zaakpermission
from zgw.models.zrc import Zaak

from .permissions import activiteiten_schrijven


def can_read_zaak(user: User, zaak: Zaak):
    return _generic_zaakpermission(user, zaak, zaken_inzien)


register(activiteiten_schrijven)(_generic_zaakpermission)


rules.add_rule("activities:read", can_read_zaak)
