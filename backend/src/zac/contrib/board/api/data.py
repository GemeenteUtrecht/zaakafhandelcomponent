from dataclasses import dataclass
from typing import List

from zgw.models import Zaak


@dataclass
class DashboardGroup:
    zaaktype_omschrijving: str
    actieve_zaken: List[Zaak]
