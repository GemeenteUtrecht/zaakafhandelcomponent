from dataclasses import dataclass
from datetime import date


@dataclass
class ReportRow:
    eigenschappen: str
    identificatie: str
    omschrijving: str
    startdatum: date
    status: str
    zaaktype_omschrijving: str
