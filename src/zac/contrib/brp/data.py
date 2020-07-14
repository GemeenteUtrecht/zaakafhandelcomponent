from dataclasses import dataclass

from zgw_consumers.api_models.base import Model


@dataclass
class IngeschrevenNatuurlijkPersoon(Model):
    burgerservicenummer: str
    geheimhouding_persoonsgegevens: bool
    geslachtsaanduiding: str
    leeftijd: int
    datum_eerste_inschrijving_gb_a: dict
    kiesrecht: dict
    naam: dict
    in_onderzoek: dict
    nationaliteit: list
    geboorte: dict
    opschorting_bijhouding: dict
    overlijden: dict
    verblijfplaats: dict
    gezagsverhouding: dict
    verblijfstitel: dict
    reisdocumenten: list
    _links: dict
    _embedded: dict

    def get_full_name(self) -> str:
        return f'{self.naam["voornamen"]} {self.naam["voorvoegsel"]} {self.naam["geslachtsnaam"]}'
