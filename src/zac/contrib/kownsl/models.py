from django.db import models
from django.utils.encoding import force_text
from django.utils.translation import gettext_lazy as _

from solo.models import SingletonModel


class KownslConfigManager(models.Manager):
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.select_related("service")


class KownslConfig(SingletonModel):
    service = models.ForeignKey(
        "zgw_consumers.Service", null=True, on_delete=models.SET_NULL
    )

    objects = KownslConfigManager()

    class Meta:
        verbose_name = _("Kownsl configuration")

    def __str__(self):
        return force_text(self._meta.verbose_name)
