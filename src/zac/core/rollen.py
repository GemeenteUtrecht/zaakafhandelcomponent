from typing import Optional

from django.utils.translation import gettext_lazy as _

from zgw_consumers.api_models.constants import RolTypes
from zgw_consumers.api_models.zaken import Rol as _Rol

from zac.contrib.brp.api import fetch_natuurlijkpersoon
from zac.contrib.brp.data import IngeschrevenNatuurlijkPersoon


class Rol(_Rol):
    _natuurlijkpersoon = None

    @property
    def natuurlijkpersoon(self) -> Optional[IngeschrevenNatuurlijkPersoon]:
        if not self._natuurlijkpersoon:
            # extract from brp
            self._natuurlijkpersoon = fetch_natuurlijkpersoon(self.betrokkene)
        return self._natuurlijkpersoon

    def get_name(self) -> Optional[str]:
        if self.betrokkene_type != RolTypes.natuurlijk_persoon:
            return None

        if self.betrokkene:
            if not self.natuurlijkpersoon:
                return _("(invalid BRP reference!)")
            return self.natuurlijkpersoon.get_full_name()

        bits = [
            self.betrokkene_identificatie["voornamen"],
            self.betrokkene_identificatie["voorvoegsel_geslachtsnaam"],
            self.betrokkene_identificatie["geslachtsnaam"],
        ]
        return " ".join(bits).strip() or _("(not set)")

    def get_bsn(self) -> Optional[str]:
        if self.betrokkene_type != RolTypes.natuurlijk_persoon:
            return None

        if self.betrokkene:
            if not self.natuurlijkpersoon:
                return _("(invalid BRP reference!)")
            return self.natuurlijkpersoon.burgerservicenummer

        return self.betrokkene_identificatie["inp_bsn"]
