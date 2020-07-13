from typing import Optional

from zgw_consumers.api_models.constants import RolTypes
from zgw_consumers.api_models.zaken import Rol


class NamedRol(Rol):
    _name = None

    def get_name(self) -> Optional[str]:
        from .services import fetch_natuurlijkpersoon

        if self.betrokkene_type != RolTypes.natuurlijk_persoon:
            return None

        # extract from brp
        if self.betrokkene:
            brp = fetch_natuurlijkpersoon(self.betrokkene)
            name = "{} {} {}".format(
                brp["voornamen"], brp["voorvoegsel"], brp["geslachtsnaam"]
            )
        else:
            name = "{} {} {}".format(
                self.betrokkene_identificatie["voornamen"],
                self.betrokkene_identificatie["voorvoegsel_geslachtsnaam"],
                self.betrokkene_identificatie["geslachtsnaam"],
            )
        return name

    @property
    def name(self):
        if not self._name:
            self._name = self.get_name()
        return self._name
