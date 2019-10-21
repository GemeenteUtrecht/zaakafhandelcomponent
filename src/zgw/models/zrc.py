import datetime
from dataclasses import dataclass, field

from django.utils.functional import cached_property

from dateutil.parser import parse
from isodate import parse_duration

from .base import Model
from .ztc import StatusType


@dataclass
class Zaak(Model):
    url: str
    identificatie: str
    bronorganisatie: str
    omschrijving: str
    toelichting: str
    zaaktype: str
    registratiedatum: str
    startdatum: str
    einddatum_gepland: str
    uiterlijke_einddatum_afdoening: str
    vertrouwelijkheidaanduiding: str
    status: str
    resultaat: str
    relevante_andere_zaken: list
    zaakgeometrie: dict

    statussen: list = field(default_factory=list)
    eigenschappen: list = field(default_factory=list)
    tasks: list = field(default_factory=list)

    @cached_property
    def deadline(self) -> datetime.date:
        from zac.core.services import get_zaaktypes

        if self.uiterlijke_einddatum_afdoening:
            return parse(self.uiterlijke_einddatum_afdoening)

        zaaktypes = get_zaaktypes()
        zt = next((zt for zt in zaaktypes if zt.url == self.zaaktype))

        start = parse(self.startdatum)
        duration = parse_duration(zt.doorlooptijd)
        return (start + duration).date()


@dataclass
class Status(Model):
    url: str
    zaak: str
    status_type: StatusType
    datum_status_gezet: str
    statustoelichting: str


@dataclass
class Eigenschap(Model):
    url: str
    zaak: Zaak
    # eigenschap: str
    naam: str
    waarde: str
