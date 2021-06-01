from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils.translation import gettext_lazy as _

from django_better_admin_arrayfield.models.fields import ArrayField


class SearchReport(models.Model):
    name = models.CharField(_("name"), max_length=100)
    query = JSONField(_("search query"))
    fields = models.TextField(_("fields"))
    zaaktypen = ArrayField(
        models.CharField(_("zaaktype identification"), max_length=50),
        verbose_name=_("zaaktypen"),
        default=list,
    )

    class Meta:
        verbose_name = _("search report")
        verbose_name_plural = _("search reports")

    def __str__(self):
        return self.name
