import logging
from typing import Optional

from django.utils.translation import gettext_lazy as _

from zgw_consumers.api_models.constants import RolTypes
from zgw_consumers.api_models.zaken import Rol as _Rol

from zac.accounts.models import Group, User
from zac.contrib.brp.api import fetch_natuurlijkpersoon
from zac.contrib.brp.data import IngeschrevenNatuurlijkPersoon
from zac.contrib.organisatieonderdelen.models import OrganisatieOnderdeel

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
        getter = GET_NAME.get(self.betrokkene_type)
        if getter is None:
            return None

        return getter(self)

    def get_identificatie(self) -> Optional[str]:
        getter = GET_IDENTIFICATIE.get(self.betrokkene_type)
        if getter is None:
            return None

        return getter(self)

    def get_roltype_omschrijving(self) -> Optional[str]:
        from zac.core.services import get_roltype

        roltype = get_roltype(self.roltype)
        return roltype.omschrijving


def get_bsn(rol: Rol) -> str:
    if rol.betrokkene:
        if not rol.natuurlijkpersoon:
            return _("(invalid BRP reference!)")
        return rol.natuurlijkpersoon.burgerservicenummer
    return rol.betrokkene_identificatie["inp_bsn"]


def get_medewerker_username(rol: Rol) -> str:
    if rol.betrokkene:
        return _("(invalid medewerker URL!)")
    return rol.betrokkene_identificatie["identificatie"]


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
    return " ".join([bit for bit in bits if bit != ""]).strip() or _("(not set)")


def get_naam_medewerker(rol: Rol) -> Optional[str]:
    if rol.betrokkene:
        logger.warning(
            "Don't know how to handle medewerker URLs (got %s)", rol.betrokkene
        )
        return f"NotImplementedError: {rol.betrokkene}"

    if username := rol.betrokkene_identificatie.get("identificatie"):
        # Identificatie of a medewerker only allows voorletters, voorvoegsel_achternaam and achternaam.
        # This is not unique enough and so we catch the gebruiker by its identificatie whenever possible.
        try:
            from zac.core.camunda.utils import resolve_assignee

            user = resolve_assignee(username)
            if isinstance(user, User):
                name = user.get_full_name()
            elif isinstance(user, Group):
                logger.warning(
                    "Groups should not be set on a ROL. Reverting to group name for now."
                )
                name = "Groep: {obj}".format(obj=user.name.lower())

        except RuntimeError:
            logger.warning(
                "Could not resolve betrokkene_identificatie.identificatie to a user. Reverting to information in betrokkene_identificatie.",
                exc_info=True,
            )
            bits = [
                rol.betrokkene_identificatie["voorletters"],
                rol.betrokkene_identificatie["voorvoegsel_achternaam"],
                rol.betrokkene_identificatie["achternaam"],
            ]
            name = (
                " ".join([bit for bit in bits if bit != ""]).strip()
                or rol.betrokkene_identificatie["identificatie"]
            )

    return name


def get_naam_organisatorische_eenheid(rol: Rol) -> str:
    identificatie = rol.betrokkene_identificatie.get("identificatie")
    organisatie_onderdeel = OrganisatieOnderdeel.objects.filter(
        slug=identificatie
    ).first()
    if organisatie_onderdeel:
        return organisatie_onderdeel.name
    return rol.betrokkene_identificatie["naam"]


def get_identificatie_organisatorische_eenheid(rol: Rol) -> str:
    return rol.betrokkene_identificatie["identificatie"]


GET_NAME = {
    RolTypes.natuurlijk_persoon: get_naam_natuurlijkpersoon,
    RolTypes.medewerker: get_naam_medewerker,
    RolTypes.organisatorische_eenheid: get_naam_organisatorische_eenheid,
}

GET_IDENTIFICATIE = {
    RolTypes.natuurlijk_persoon: get_bsn,
    RolTypes.medewerker: get_medewerker_username,
    RolTypes.organisatorische_eenheid: get_identificatie_organisatorische_eenheid,
}
