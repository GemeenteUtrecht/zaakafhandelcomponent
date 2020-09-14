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
    _links: Optional[dict] = None
    _embedded: Optional[dict] = None
    geboorte: Optional[dict] = None
    verblijfplaats: Optional[dict] = None

    def clear_whitespaces(self, string: str) -> str:
        return " ".join(string.split())

    def clean_verblijfplaats(self) -> Optional[dict]:
        if not self.verblijfplaats:
            return None

        huisnummer = self.verblijfplaats.get("huisnummer", "")
        straatnaam = self.verblijfplaats.get("straatnaam", "")
        adres = self.clear_whitespaces(f"{straatnaam} {huisnummer}")
        woonplaats = self.verblijfplaats.get("woonplaatsnaam", "")
        postcode = self.verblijfplaats.get("postcode", "")

        self.verblijfplaats = {
            "adres": adres,
            "woonplaats": woonplaats,
            "postcode": postcode,
        }

    def get_basic_info_person(self, persons: list) -> Optional[list]:
        if not persons:
            return None

        persons_clean = []
        for person in persons:
            naam = person.get("naam", "")
            if naam:
                voorletters = naam.get("voorletters", "")
                geslachtsnaam = naam.get("geslachtsnaam", "")
                voorvoegsel = naam.get("voorvoegsel", "")

                # Remove multiple white spaces with " ".join(x.split())
                naam = self.clear_whitespaces(
                    f"{voorletters} {voorvoegsel} {geslachtsnaam}"
                )

            geboorte = person.get("geboorte", {}).get("datum", {}).get("datum", "")
            burgerservicenummer = person.get("burgerservicenummer", "")

            persons_clean.append(
                {
                    "naam": naam,
                    "geboortedatum": geboorte,
                    "burgerservicenummer": burgerservicenummer,
                }
            )

        return persons_clean

    @property
    def geboortedatum(self) -> Optional[str]:
        if self.geboorte and "datum" in self.geboorte:
            return self.geboorte["datum"]["datum"]
        return None

    @property
    def geboorteland(self) -> Optional[str]:
        if self.geboorte and "land" in self.geboorte:
            return self.geboorte["land"]["omschrijving"]
        return None

    @property
    def kinderen(self) -> Optional[list]:
        if self._embedded:
            kinderen = self._embedded.get("kinderen", [])
            return self.get_basic_info_person(kinderen)
        return None

    @property
    def partners(self) -> Optional[list]:
        if self._embedded:
            partners = self._embedded.get("partners", [])
            return self.get_basic_info_person(partners)
        return None
