from django.db import models
from django.utils.encoding import force_text
from django.utils.translation import gettext_lazy as _

from solo.models import SingletonModel


class KownslConfig(SingletonModel):
    service = models.ForeignKey(
        "zgw_consumers.Service", null=True, on_delete=models.SET_NULL
    )

    class Meta:
        verbose_name = _("Kownsl configuration")

    def __str__(self):
        return force_text(self._meta.verbose_name)
