from typing import Union

import rules
from zgw_consumers.api_models.zaken import Zaak

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

    zaaktype_url = zaak.zaaktype
    if not isinstance(zaaktype_url, str):
        zaaktype_url = zaaktype_url.url

    permissions = user._zaaktype_perms
    return permissions.contains(
        permission=zaken_inzien.name,
        zaaktype=zaaktype_url,
        vertrouwelijkheidaanduiding=zaak.vertrouwelijkheidaanduiding,
    )


rules.add_rule(zaken_inzien.name, can_read_zaak)
