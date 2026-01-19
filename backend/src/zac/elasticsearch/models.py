from django.db import models
from django.db.models import JSONField
from django.utils.translation import gettext_lazy as _


class SearchReport(models.Model):
    """
    A search report saves search-criteria.
    """

    name = models.CharField(_("name"), max_length=100)
    query = JSONField(_("search query"))

    class Meta:
        verbose_name = _("search report")
        verbose_name_plural = _("search reports")

    def __str__(self):
        return self.name
