from django.db import models
from django.utils.translation import gettext_lazy as _


class KillableTask(models.Model):
    """
    Holds the name of a camunda task that can be canceled.

    """

    name = models.CharField(_("task name"), max_length=100, unique=True)

    class Meta:
        verbose_name = _("camunda task")
        verbose_name_plural = _("camunda tasks")

    def __str__(self):
        return self.name
