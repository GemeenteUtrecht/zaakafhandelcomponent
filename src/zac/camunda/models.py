import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class UserTaskCallback(models.Model):
    """
    Model an expected user task callback.

    When an external application is done preparing their data, they send a callback
    to an endpoint. This model tracks which callback is for which user task.
    """

    callback_id = models.UUIDField(default=uuid.uuid4, editable=False)
    task_id = models.UUIDField(_("user task ID"))
    callback_received = models.BooleanField(default=False)

    class Meta:
        verbose_name = _("user task callback")
        verbose_name_plural = _("user task callbacks")

    def __str__(self):
        return str(self.task_id)
