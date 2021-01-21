from dataclasses import dataclass

from zgw_consumers.api_models.base import Model


@dataclass
class DowcResponse(Model):
    purpose: str
    uuid: str
    magic_url: str
