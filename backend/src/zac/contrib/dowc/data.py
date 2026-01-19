from dataclasses import dataclass
from uuid import UUID

from zgw_consumers.api_models.base import Model


@dataclass
class DowcResponse(Model):
    drc_url: str
    magic_url: str
    purpose: str
    uuid: UUID
    unversioned_url: str


@dataclass
class OpenDowc(Model):
    document: str
    uuid: UUID
    locked_by: str
