from dataclasses import dataclass
from datetime import datetime
from typing import List

from django.utils.translation import gettext_lazy as _

from zgw_consumers.api_models.base import Model

from zac.accounts.models import User
from zac.core.camunda.utils import resolve_assignee


@dataclass
class Oudbehandelaar(Model):
    email: str
    ended: datetime
    started: datetime
    identificatie: str

    @property
    def user(self) -> User:
        return resolve_assignee(self.identificatie)


@dataclass
class Oudbehandelaren(Model):
    behandelaren: List[Oudbehandelaar]
    zaak: str
