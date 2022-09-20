from dataclasses import dataclass
from typing import List

from zgw_consumers.api_models.base import Model


@dataclass
class ProcessEigenschapChoice(Model):
    value: str
    label: str


@dataclass
class ProcessEigenschap(Model):
    eigenschapnaam: str
    default: str
    label: str
    required: bool
    order: int


@dataclass
class ProcessRol(Model):
    roltype_omschrijving: str
    betrokkene_type: str
    label: str
    required: bool
    order: int


@dataclass
class ProcessInformatieObject(Model):
    informatieobjecttype_omschrijving: str
    allow_multiple: bool
    label: str
    required: bool
    order: int


@dataclass
class StartCamundaProcessForm(Model):
    zaaktype_catalogus: str
    zaaktype_identificaties: List[str]
    camunda_process_definition_key: str
    process_eigenschappen: List[ProcessEigenschap]
    process_rollen: List[ProcessRol]
    process_informatie_objecten: List[ProcessInformatieObject]
