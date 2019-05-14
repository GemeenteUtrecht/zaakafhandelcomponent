from dataclasses import dataclass
from typing import Any

from .base import Model
from .ztc import InformatieObjectType


@dataclass
class Document(Model):
    url: str
    auteur: str
    beschrijving: str
    bestandsnaam: str
    bestandsomvang: int
    bronorganisatie: str
    creatiedatum: str
    formaat: str  # noqa
    identificatie: str
    indicatie_gebruiksrecht: Any
    informatieobjecttype: InformatieObjectType
    inhoud: str
    integriteit: dict
    link: str
    ondertekening: dict
    ontvangstdatum: Any
    status: str
    taal: str
    titel: str
    vertrouwelijkheidaanduiding: str
    verzenddatum: str
