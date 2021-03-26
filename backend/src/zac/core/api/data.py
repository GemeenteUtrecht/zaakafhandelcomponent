from dataclasses import dataclass

from zgw_consumers.api_models.base import Model


@dataclass
class VertrouwelijkheidsAanduidingData(Model):
    label: str
    value: str
