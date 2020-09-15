import logging
from typing import Optional

from django.utils.translation import gettext_lazy as _

from zgw_consumers.api_models.constants import RolTypes
from zgw_consumers.api_models.zaken import Rol as _Rol

from zac.contrib.brp.api import fetch_natuurlijkpersoon
from zac.contrib.brp.data import IngeschrevenNatuurlijkPersoon

logger = logging.getLogger(__name__)


class Rol(_Rol):
    _natuurlijkpersoon = None

    @property
    def natuurlijkpersoon(self) -> Optional[IngeschrevenNatuurlijkPersoon]:
        if not self._natuurlijkpersoon:
            # extract from brp
            self._natuurlijkpersoon = fetch_natuurlijkpersoon(self.betrokkene)
        return self._natuurlijkpersoon

    def get_name(self) -> Optional[str]:
        get_name = GET_NAME.get(self.betrokkene_type)
        if get_name is None:
            return None

        return get_name(self)

    def get_bsn(self) -> Optional[str]:
        if self.betrokkene_type != RolTypes.natuurlijk_persoon:
            return None

        if self.betrokkene:
            if not self.natuurlijkpersoon:
                return _("(invalid BRP reference!)")
            return self.natuurlijkpersoon.burgerservicenummer

        return self.betrokkene_identificatie["inp_bsn"]


def get_naam_natuurlijkpersoon(rol: Rol) -> Optional[str]:
    if rol.betrokkene:
        if not rol.natuurlijkpersoon:
            return _("(invalid BRP reference!)")
        return rol.natuurlijkpersoon.get_full_name()

    bits = [
        rol.betrokkene_identificatie["voornamen"],
        rol.betrokkene_identificatie["voorvoegsel_geslachtsnaam"],
        rol.betrokkene_identificatie["geslachtsnaam"],
    ]
    return " ".join(bits).strip() or _("(not set)")


def get_naam_medewerker(rol: Rol) -> Optional[str]:
    if rol.betrokkene:
        logger.warning(
            "Don't know how to handle medewerker URLs (got %s)", rol.betrokkene
        )
        return f"NotImplementedError: {rol.betrokkene}"

    bits = [
        rol.betrokkene_identificatie["voorletters"],
        rol.betrokkene_identificatie["voorvoegsel_achternaam"],
        rol.betrokkene_identificatie["achternaam"],
    ]
    return " ".join(bits).strip() or rol.betrokkene_identificatie["identificatie"]


GET_NAME = {
    RolTypes.natuurlijk_persoon: get_naam_natuurlijkpersoon,
    RolTypes.medewerker: get_naam_medewerker,
}
