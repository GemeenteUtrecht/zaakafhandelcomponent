from dataclasses import dataclass
from typing import List, Optional

from zgw_consumers.api_models.base import Model

from zac.accounts.models import User
from zac.core.camunda.utils import resolve_assignee

from ..user_tasks.data import Task


@dataclass
class HistoricUserTask(Model):
    history: List[dict]
    task: Task

    @property
    def assignee(self) -> Optional[User]:
        if not self.task.assignee:
            return None
        return resolve_assignee(self.task.assignee)
