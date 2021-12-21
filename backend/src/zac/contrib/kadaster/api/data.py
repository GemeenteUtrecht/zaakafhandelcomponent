from dataclasses import dataclass
from typing import List

from zgw_consumers.api_models.base import Model


@dataclass
class SpellSuggestions(Model):
    search_term: str
    num_found: int
    start_offset: int
    end_offset: int
    suggestion: List[str]


@dataclass
class SpellCheck(Model):
    suggestions: List[SpellSuggestions]


@dataclass
class SuggestResult(Model):
    type: str
    weergavenaam: str
    id: str
    score: float


@dataclass
class BagLocation(Model):
    num_found: int
    start: int
    max_score: float
    docs: List[SuggestResult]


@dataclass
class AddressSearchResponse(Model):
    response: BagLocation
    spellcheck: SpellCheck


@dataclass
class Address(Model):
    straatnaam: str
    nummer: str
    gemeentenaam: str
    postcode: str = ""
    provincienaam: str = ""


@dataclass
class BaseBagData(Model):
    url: str
    geometrie: dict
    status: str


@dataclass
class PandBagData(BaseBagData):
    oorspronkelijk_bouwjaar: int


@dataclass
class VerblijfsobjectBagData(BaseBagData):
    oppervlakte: int


@dataclass
class Pand(Model):
    adres: Address
    bag_object: PandBagData


@dataclass
class Verblijfsobject(Model):
    adres: Address
    bag_object: VerblijfsobjectBagData
