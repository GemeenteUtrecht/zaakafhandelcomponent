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
