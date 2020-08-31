from dataclasses import dataclass
from typing import Optional

from zgw_consumers.api_models.base import Model


@dataclass
class IngeschrevenNatuurlijkPersoon(Model):
    burgerservicenummer: str
    geslachtsaanduiding: str
    leeftijd: int
    naam: dict
    geboorte: dict
    _links: dict
    kiesrecht: Optional[dict] = None

    def get_full_name(self) -> str:
        bits = [
            self.naam["voornamen"],
            self.naam.get("voorvoegsel", ""),
            self.naam["geslachtsnaam"],
        ]
        return " ".join(bits)


@dataclass
class ExtraInformatieIngeschrevenNatuurlijkPersoon(Model):
    geboorte: Optional[dict] = None
    verblijfplaats: Optional[dict] = None
    _links: Optional[dict] = None

    @property
    def partners(self) -> Optional[list]:
        return self._links.get('partners')

    @property
    def kinderen(self) -> Optional[list]:
        return self._links.get('kinderen')

    @property
    def geboortedatum(self) -> Optional[str]:
        if self.geboorte and 'datum' in self.geboorte:
            return self.geboorte['datum']['datum']
        return None

    @property
    def geboorteland(self) -> Optional[str]:
        if self.geboorte and 'land' in self.geboorte:
            return self.geboorte['land']['omschrijving']
        return None
