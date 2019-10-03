from dataclasses import dataclass, field

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
    vertrouwelijkheidaanduiding: str
    status: str
    resultaat: str
    relevante_andere_zaken: list
    tasks: list = field(default_factory=list)


@dataclass
class Status(Model):
    url: str
    zaak: str
    status_type: StatusType
    datum_status_gezet: str
    statustoelichting: str
