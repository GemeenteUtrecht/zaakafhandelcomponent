from typing import Union

import rules
from zgw_consumers.api_models.constants import VertrouwelijkheidsAanduidingen
from zgw_consumers.api_models.zaken import Zaak

from zac.accounts.permissions import VA_ORDER, PermissionSet
from zac.core.services import fetch_zaaktype

from .permissions import zaken_inzien


class dictwrapper:
    def __init__(self, obj):
        self._obj = obj

    def __getattr__(self, attr: str):
        if hasattr(self._obj, attr):
            return getattr(self._obj, attr)

        if attr in self._obj:
            return self._obj[attr]

        raise AttributeError(f"Obj {self._obj} has no attribute '{attr}'")


@rules.predicate
def can_read_zaak(user, zaak: Union[dict, Zaak]):
    zaak = dictwrapper(zaak)

    zaaktype = zaak.zaaktype
    if isinstance(zaaktype, str):
        zaaktype = fetch_zaaktype(zaaktype)

    zt_identificatie = zaaktype.identificatie

    zaak_va = VA_ORDER[zaak.vertrouwelijkheidaanduiding]

    # check permission sets
    perm_sets = (
        PermissionSet.objects.filter(
            authorizationprofile__user=user,
            catalogus=zaaktype.catalogus,
            permissions__contains=[zaken_inzien.name],
            zaaktype_identificaties__contains=[zt_identificatie],
        )
        .annotate(
            _max_va_order=VertrouwelijkheidsAanduidingen.get_order_expression("max_va")
        )
        .filter(_max_va_order__gte=zaak_va)
    )

    return perm_sets.exists()


rules.add_rule(zaken_inzien.name, can_read_zaak)
