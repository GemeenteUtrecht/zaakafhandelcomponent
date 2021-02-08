from dataclasses import dataclass
from uuid import UUID

from zgw_consumers.api_models.base import Model


@dataclass
class DowcResponse(Model):
    purpose: str
    uuid: UUID
    magic_url: str
