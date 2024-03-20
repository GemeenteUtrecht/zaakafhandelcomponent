from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from django.utils.translation import gettext_lazy as _

from zgw_consumers.api_models.base import Model

from zac.accounts.models import User
from zac.camunda.constants import AssigneeTypeChoices
from zac.core.camunda.utils import resolve_assignee


@dataclass
class Oudbehandelaar(Model):
    email: str
    ended: datetime
    started: datetime
    identificatie: str
    changed_by: str

    @property
    def user(self) -> User:
        return resolve_assignee(self.identificatie)

    @property
    def changer(self) -> Optional[User]:
        if self.changed_by.startswith(AssigneeTypeChoices.user):
            return resolve_assignee(self.changed_by)
        return None


@dataclass
class Oudbehandelaren(Model):
    oudbehandelaren: List[Oudbehandelaar]
    zaak: str
