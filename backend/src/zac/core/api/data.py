from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from zgw_consumers.api_models.base import Model


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
    wijzigingen: AuditTrailWijzigingenData
    resource_url: str

    @property
    def was_bumped(self) -> bool:
        if self.wijzigingen.nieuw.version_label:
            return True
        return False

    @property
    def last_edited_date(self) -> datetime:
        if modified := self.wijzigingen.nieuw.modified:
            return modified
        return self.aanmaakdatum
