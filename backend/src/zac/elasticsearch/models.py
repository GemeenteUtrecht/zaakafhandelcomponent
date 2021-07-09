from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils.translation import gettext_lazy as _


class SearchReport(models.Model):
    name = models.CharField(_("name"), max_length=100)
    query = JSONField(_("search query"))

    class Meta:
        verbose_name = _("search report")
        verbose_name_plural = _("search reports")

    def __str__(self):
        return self.name
