"""
Datamodels for ZGW resources.

These are NOT django models.
"""
from dataclasses import dataclass

from .camel_case import underscoreize


class Model:

    @property
    def id(self):
        """
        Because of the usage of UUID4, we can rely on the UUID as identifier.
        """
        return self.url.split('/')[-1]

    @classmethod
    def from_raw(cls, raw_data: dict, strict=False):
        kwargs = underscoreize(raw_data)
        # strip out the unknown keys
        if not strict:
            known_keys = cls.__annotations__.keys()
            init_kwargs = {
                key: value
                for key, value
                in kwargs.items() if key in known_keys
            }
        else:
            init_kwargs = kwargs

        return cls(**init_kwargs)


@dataclass
class ZaakType(Model):
    url: str
    catalogus: str
    identificatie: int
    omschrijving: str
    omschrijving_generiek: str
    vertrouwelijkheidaanduiding: str


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


@dataclass
class Status(Model):
    url: str
    zaak: str
    status_type: str
    datum_status_gezet: str
    statustoelichting: str


@dataclass
class StatusType(Model):
    url: str
    zaaktype: str
    omschrijving: str
    omschrijving_generiek: str
    statustekst: str
    volgnummer: int
    is_eindstatus: bool
