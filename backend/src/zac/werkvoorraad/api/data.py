from dataclasses import dataclass
from typing import List

from zac.accounts.models import AccessRequest
from zac.activities.models import Activity
from zgw.models import Zaak


@dataclass
class ActivityGroup:
    activities: List[Activity]
    zaak: Zaak
    zaak_url: str


@dataclass
class AccessRequestGroup:
    access_requests: List[AccessRequest]
    zaak: Zaak
    zaak_url: str
