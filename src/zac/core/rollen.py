from typing import Optional

from zgw_consumers.api_models.constants import RolTypes
from zgw_consumers.api_models.zaken import Rol

from zac.contrib.brp.api import fetch_natuurlijkpersoon


def display_rol_name(rol: Rol) -> Optional[str]:
    if rol.betrokkene_type != RolTypes.natuurlijk_persoon:
        return None

    # extract from brp
    if rol.betrokkene:
        brp_natuurlijkpersoon = fetch_natuurlijkpersoon(rol.betrokkene)
        name = brp_natuurlijkpersoon.get_full_name()
    else:
        name = "{} {} {}".format(
            rol.betrokkene_identificatie["voornamen"],
            rol.betrokkene_identificatie["voorvoegsel_geslachtsnaam"],
            rol.betrokkene_identificatie["geslachtsnaam"],
        )
    return name
