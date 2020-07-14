from dataclasses import dataclass

from zgw_consumers.api_models.base import Model


@dataclass
class IngeschrevenNatuurlijkPersoon(Model):
    burgerservicenummer: str
    geslachtsaanduiding: str
    leeftijd: int
    kiesrecht: dict
    naam: dict
    geboorte: dict
    _links: dict

    def get_full_name(self) -> str:
        return f'{self.naam["voornamen"]} {self.naam["voorvoegsel"]} {self.naam["geslachtsnaam"]}'
