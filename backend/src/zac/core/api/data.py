from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from zgw_consumers.api_models.base import Model, factory


@dataclass
class VertrouwelijkheidsAanduidingData(Model):
    label: str
    value: str


@dataclass
class AuditTrailWijzigingsData(Model):
    modified: Optional[datetime] = None
    author: Optional[str] = None
    version_label: Optional[str] = None


@dataclass
class AuditTrailWijzigingenData(Model):
    oud: AuditTrailWijzigingsData
    nieuw: AuditTrailWijzigingsData


@dataclass
class AuditTrailData(Model):
    aanmaakdatum: datetime
    wijzigingen: List[AuditTrailWijzigingenData]
    resource_url: str

    @property
    def was_bumped(self) -> bool:
        if self.wijzigingen.nieuw.version_label:
            return True
        return False
