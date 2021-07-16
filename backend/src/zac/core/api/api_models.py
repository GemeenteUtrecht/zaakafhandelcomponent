from dataclasses import dataclass
from datetime import date
from typing import Optional

from zgw_consumers.api_models.base import ZGWModel


# TODO Move to ZGW_consumers?
@dataclass
class Objecttype(ZGWModel):
    url: str
    name: str
    name_plural: str
    description: Optional[str]
    data_classification: Optional[str]
    maintainer_organization: Optional[str]
    maintainer_department: Optional[str]
    contact_person: Optional[str]
    contact_email: Optional[str]
    source: Optional[str]
    update_frequency: Optional[str]
    provider_organization: Optional[str]
    documentation_url: Optional[str]
    labels: Optional[dict]
    created_at: Optional[date]
    modified_at: Optional[date]
    versions: Optional[list]


@dataclass
class ObjecttypeVersion(ZGWModel):
    url: str
    version: Optional[int]
    object_type: Optional[str]
    status: Optional[str]
    json_schema: Optional[dict]
    created_at: Optional[date]
    modified_at: Optional[date]
    published_at: Optional[date]


@dataclass
class Record(ZGWModel):
    index: Optional[int]
    type_version: Optional[int]
    data: Optional[dict]
    geometry: Optional[dict]
    start_at: Optional[date]
    end_at: Optional[date]
    registration_at: Optional[date]
    correction_for: Optional[str]
    corrected_by: Optional[str]


@dataclass
class Object(ZGWModel):
    url: str
    type: str
    record: Record
