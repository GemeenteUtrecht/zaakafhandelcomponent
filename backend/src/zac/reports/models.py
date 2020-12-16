from django.db import models
from django.utils.translation import gettext_lazy as _

from django_better_admin_arrayfield.models.fields import ArrayField


class Report(models.Model):
    name = models.CharField(_("name"), max_length=100)
    zaaktypen = ArrayField(
        models.CharField(_("zaaktype identification"), max_length=50),
        verbose_name=_("zaaktypen"),
        default=list,
    )

    class Meta:
        verbose_name = _("report")
        verbose_name_plural = _("reports")

    def __str__(self):
        return self.name
