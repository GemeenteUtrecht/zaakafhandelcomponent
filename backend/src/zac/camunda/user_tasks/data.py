from dataclasses import dataclass

from ..data import Task
from .context import Context


@dataclass
class UserTaskData:
    task: Task
    context: Context
