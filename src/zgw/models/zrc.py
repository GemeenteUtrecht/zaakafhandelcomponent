import datetime
from dataclasses import dataclass, field

from django.utils.functional import cached_property

from dateutil.parser import parse
from isodate import parse_duration
from zgw_consumers.api_models.zaken import Zaak as _Zaak

from .base import Model
from .ztc import StatusType, ZaakType


@dataclass
class Zaak(_Zaak):
    statussen: list = field(default_factory=list)
    eigenschappen: list = field(default_factory=list)
    tasks: list = field(default_factory=list)

    def get_zaaktype(self) -> ZaakType:
        from zac.core.services import get_zaaktypes

        zaaktypes = get_zaaktypes()
        zt = next((zt for zt in zaaktypes if zt.url == self.zaaktype))
        return zt

    @cached_property
    def deadline(self) -> datetime.date:
        if self.uiterlijke_einddatum_afdoening:
            return parse(self.uiterlijke_einddatum_afdoening)

        zt = self.get_zaaktype()
        start = parse(self.startdatum)
        duration = parse_duration(zt.doorlooptijd)
        return (start + duration).date()

    @cached_property
    def status_information(self) -> dict:
        """
        Fetch the current status in context of all statusses.
        """
        from zac.core.services import get_statustypen

        zaaktype = self.get_zaaktype()
        statustypen = get_statustypen(zaaktype)

        if self.status is None:
            return {"volgnummer": 0, "omschrijving": "", "totaal": len(statustypen)}

        current_status = next(
            (status for status in self.statussen if status.url == self.status)
        )

        return {
            "volgnummer": current_status.status_type.volgnummer,
            "omschrijving": current_status.status_type.omschrijving,
            "totaal": len(statustypen),
        }


@dataclass
class Status(Model):
    url: str
    zaak: str
    statustype: StatusType
    datum_status_gezet: str
    statustoelichting: str


@dataclass
class Eigenschap(Model):
    url: str
    zaak: Zaak
    # eigenschap: str
    naam: str
    waarde: str
