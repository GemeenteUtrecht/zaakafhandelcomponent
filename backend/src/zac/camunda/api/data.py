from dataclasses import dataclass
from typing import Any, List, Optional

from zac.accounts.models import User
from zac.core.camunda.utils import resolve_assignee

from ..user_tasks.data import Task


@dataclass
class HistoricActivityInstanceDetail:
    variable_name: str
    value: Any
    label: Optional[str] = None


@dataclass
class HistoricUserTask:
    history: List[HistoricActivityInstanceDetail]
    task: Task

    @property
    def assignee(self) -> Optional[User]:
        if not self.task.assignee:
            return None
        return resolve_assignee(self.task.assignee)
