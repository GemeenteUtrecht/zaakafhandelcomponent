import datetime
from dataclasses import dataclass, field

from django.utils import timezone
from django.utils.functional import cached_property

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
        if not self.uiterlijke_einddatum_afdoening:
            zt = self.get_zaaktype()
            end = self.startdatum + zt.doorlooptijd
            self.uiterlijke_einddatum_afdoening = end
        return self.uiterlijke_einddatum_afdoening

    def deadline_progress(self) -> float:
        today = timezone.now().date()
        total_duration = (self.deadline - self.startdatum).days
        spent_duration = (today - self.startdatum).days
        return round(spent_duration / total_duration * 100, 2)

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
class Eigenschap(Model):
    url: str
    zaak: Zaak
    # eigenschap: str
    naam: str
    waarde: str
