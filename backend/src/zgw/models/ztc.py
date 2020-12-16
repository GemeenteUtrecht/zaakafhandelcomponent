from dataclasses import dataclass

from .base import Model


@dataclass
class ZaakType(Model):
    url: str
    catalogus: str
    identificatie: int
    omschrijving: str
    omschrijving_generiek: str
    vertrouwelijkheidaanduiding: str
    aanleiding: str
    toelichting: str
    doorlooptijd: str


@dataclass
class StatusType(Model):
    url: str
    zaaktype: str
    omschrijving: str
    omschrijving_generiek: str
    statustekst: str
    volgnummer: int
    is_eindstatus: bool


@dataclass
class InformatieObjectType(Model):
    url: str
    catalogus: str
    omschrijving: str
    vertrouwelijkheidaanduiding: str
