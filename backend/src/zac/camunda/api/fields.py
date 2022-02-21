from typing import Optional

from django.utils.translation import gettext_lazy as _

from rest_framework.fields import UUIDField

from ..data import Task
from ..user_tasks import get_task


class TaskField(UUIDField):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        kwargs["write_only"] = True
        self.default_error_messages["not_found"] = _(
            "The task with given `id` does not exist (anymore)."
        )

    def to_internal_value(self, data) -> Optional[Task]:
        task_id = super().to_internal_value(data)
        task = get_task(task_id, check_history=False)
        if not task:
            self.fail("not_found", value=data)
        return task
