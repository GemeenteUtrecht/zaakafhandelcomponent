import datetime
from dataclasses import dataclass, field

from django.utils import timezone
from django.utils.functional import cached_property

from zgw_consumers.api_models.base import ZGWModel
from zgw_consumers.api_models.zaken import Zaak as _Zaak


@dataclass
class Zaak(_Zaak):
    statussen: list = field(default_factory=list)
    eigenschappen: list = field(default_factory=list)
    tasks: list = field(default_factory=list)

    @cached_property
    def deadline(self) -> datetime.date:
        if not self.uiterlijke_einddatum_afdoening:
            return self.startdatum + self.zaaktype.doorlooptijd

        return self.uiterlijke_einddatum_afdoening

    def deadline_progress(self) -> float:
        today = timezone.now().date()
        total_duration = (self.deadline - self.startdatum).days
        spent_duration = (today - self.startdatum).days
        if spent_duration >= total_duration:
            return 100.0
        return round(spent_duration / total_duration * 100, 2)


@dataclass
class ZaakInformatieObject(ZGWModel):
    url: str
    zaak: str
    informatieobject: str
    aard_relatie_weergave: str
    titel: str
    beschrijving: str
    registratiedatum: datetime.datetime
